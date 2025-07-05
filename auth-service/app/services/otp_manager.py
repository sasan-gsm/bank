"""OTP (One-Time Password) manager for generating, validating, and managing OTPs."""

import pyotp
import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repository import OTPRepository
from app.core.cache import cache_manager
import logging

logger = logging.getLogger(__name__)


class OTPManager:
    """Manager for OTP operations including generation, validation, and cleanup."""
    
    def __init__(self):
        """Initialize OTP manager with configuration."""
        self.otp_length = settings.otp_length
        self.otp_expire_minutes = settings.otp_expire_minutes
        self.max_attempts = 3  # Maximum verification attempts
        self.rate_limit_window = 300  # 5 minutes in seconds
        self.max_requests_per_window = 5  # Maximum OTP requests per window
    
    def generate_otp(self, length: Optional[int] = None) -> str:
        """Generate a random numeric OTP."""
        length = length or self.otp_length
        
        # Generate random numeric OTP
        otp = ''.join([str(secrets.randbelow(10)) for _ in range(length)])
        
        logger.info(f"Generated OTP of length {length}")
        return otp
    
    def generate_totp_secret(self) -> str:
        """Generate a TOTP secret for time-based OTP."""
        return pyotp.random_base32()
    
    def generate_totp(self, secret: str) -> str:
        """Generate time-based OTP using TOTP."""
        totp = pyotp.TOTP(secret)
        return totp.now()
    
    def verify_totp(self, secret: str, otp_code: str, window: int = 1) -> bool:
        """Verify time-based OTP."""
        totp = pyotp.TOTP(secret)
        return totp.verify(otp_code, valid_window=window)
    
    async def check_rate_limit(self, user_id: int, purpose: str) -> bool:
        """Check if user has exceeded OTP request rate limit."""
        cache_key = f"otp_rate_limit:{user_id}:{purpose}"
        
        # Get current request count
        current_count = await cache_manager.get_cache(cache_key)
        
        if current_count is None:
            # First request in the window
            await cache_manager.set_cache(cache_key, 1, ttl=self.rate_limit_window)
            return True
        
        if int(current_count) >= self.max_requests_per_window:
            logger.warning(f"Rate limit exceeded for user {user_id}, purpose {purpose}")
            return False
        
        # Increment counter
        await cache_manager.set_cache(
            cache_key, 
            int(current_count) + 1, 
            ttl=self.rate_limit_window
        )
        return True
    
    async def check_verification_attempts(self, user_id: int, purpose: str) -> bool:
        """Check if user has exceeded verification attempts."""
        cache_key = f"otp_attempts:{user_id}:{purpose}"
        
        # Get current attempt count
        current_attempts = await cache_manager.get_cache(cache_key)
        
        if current_attempts is None:
            return True
        
        if int(current_attempts) >= self.max_attempts:
            logger.warning(f"Max verification attempts exceeded for user {user_id}, purpose {purpose}")
            return False
        
        return True
    
    async def increment_verification_attempts(self, user_id: int, purpose: str) -> None:
        """Increment verification attempt counter."""
        cache_key = f"otp_attempts:{user_id}:{purpose}"
        
        # Get current attempt count
        current_attempts = await cache_manager.get_cache(cache_key)
        
        if current_attempts is None:
            await cache_manager.set_cache(cache_key, 1, ttl=self.otp_expire_minutes * 60)
        else:
            await cache_manager.set_cache(
                cache_key, 
                int(current_attempts) + 1, 
                ttl=self.otp_expire_minutes * 60
            )
    
    async def clear_verification_attempts(self, user_id: int, purpose: str) -> None:
        """Clear verification attempt counter after successful verification."""
        cache_key = f"otp_attempts:{user_id}:{purpose}"
        await cache_manager.delete_cache(cache_key)
    
    async def verify_otp(
        self,
        user_id: int,
        otp_code: str,
        purpose: str,
        db: AsyncSession
    ) -> bool:
        """Verify OTP code for a user and purpose."""
        # Check verification attempts
        if not await self.check_verification_attempts(user_id, purpose):
            return False
        
        otp_repo = OTPRepository(db)
        
        # Get valid OTP for user and purpose
        otp = await otp_repo.get_valid_otp(user_id, purpose)
        
        if not otp:
            await self.increment_verification_attempts(user_id, purpose)
            logger.warning(f"No valid OTP found for user {user_id}, purpose {purpose}")
            return False
        
        # Check if OTP has expired
        if otp.created_at + timedelta(minutes=self.otp_expire_minutes) < datetime.utcnow():
            await self.increment_verification_attempts(user_id, purpose)
            logger.warning(f"Expired OTP for user {user_id}, purpose {purpose}")
            return False
        
        # Verify OTP code
        if otp.code != otp_code:
            await self.increment_verification_attempts(user_id, purpose)
            logger.warning(f"Invalid OTP code for user {user_id}, purpose {purpose}")
            return False
        
        # Mark OTP as used
        otp.is_used = True
        await db.commit()
        
        # Clear verification attempts
        await self.clear_verification_attempts(user_id, purpose)
        
        logger.info(f"OTP verified successfully for user {user_id}, purpose {purpose}")
        return True
    
    async def invalidate_user_otps(
        self,
        user_id: int,
        purpose: str,
        db: AsyncSession
    ) -> None:
        """Invalidate all OTPs for a user and purpose."""
        otp_repo = OTPRepository(db)
        await otp_repo.invalidate_user_otps(user_id, purpose)
        
        # Clear rate limiting and attempt counters
        await cache_manager.delete_cache(f"otp_rate_limit:{user_id}:{purpose}")
        await cache_manager.delete_cache(f"otp_attempts:{user_id}:{purpose}")
        
        logger.info(f"Invalidated all OTPs for user {user_id}, purpose {purpose}")
    
    async def cleanup_expired_otps(self, db: AsyncSession) -> int:
        """Clean up expired OTPs from database."""
        otp_repo = OTPRepository(db)
        
        # Calculate expiry time
        expiry_time = datetime.utcnow() - timedelta(minutes=self.otp_expire_minutes)
        
        # Delete expired OTPs
        deleted_count = await otp_repo.delete_expired_otps(expiry_time)
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired OTPs")
        
        return deleted_count
    
    async def get_otp_status(
        self,
        user_id: int,
        purpose: str,
        db: AsyncSession
    ) -> dict:
        """Get OTP status for a user and purpose."""
        otp_repo = OTPRepository(db)
        
        # Get valid OTP
        otp = await otp_repo.get_valid_otp(user_id, purpose)
        
        if not otp:
            return {
                "has_valid_otp": False,
                "remaining_attempts": self.max_attempts,
                "rate_limited": False
            }
        
        # Check expiry
        expires_at = otp.created_at + timedelta(minutes=self.otp_expire_minutes)
        is_expired = expires_at < datetime.utcnow()
        
        # Get remaining attempts
        attempts_cache_key = f"otp_attempts:{user_id}:{purpose}"
        current_attempts = await cache_manager.get_cache(attempts_cache_key)
        remaining_attempts = self.max_attempts - (int(current_attempts) if current_attempts else 0)
        
        # Check rate limiting
        rate_limited = not await self.check_rate_limit(user_id, purpose)
        
        return {
            "has_valid_otp": not is_expired and not otp.is_used,
            "expires_at": expires_at.isoformat() if not is_expired else None,
            "remaining_attempts": max(0, remaining_attempts),
            "rate_limited": rate_limited,
            "otp_id": otp.id if not is_expired and not otp.is_used else None
        }