"""Password management routes for OTP, password reset, and password change."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.db.repository import UserRepository, OTPRepository
from app.domain.models import User
from app.domain.schemas import OTPCreate
from app.core.security import security
from app.services.otp_manager import OTPManager
from app.services.email import EmailService
from app.streams.events import PasswordResetRequestedEvent, PasswordChangedEvent

router = APIRouter()


class PasswordResetRequest(BaseModel):
    """Password reset request model."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model."""
    email: EmailStr
    otp_code: str
    new_password: str


class PasswordChangeRequest(BaseModel):
    """Password change request model."""
    current_password: str
    new_password: str


class OTPRequest(BaseModel):
    """OTP generation request model."""
    email: EmailStr
    purpose: str = "password_reset"


class OTPVerification(BaseModel):
    """OTP verification model."""
    email: EmailStr
    otp_code: str
    purpose: str = "password_reset"


@router.post("/request-reset")
async def request_password_reset(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Request password reset via email OTP."""
    user_repo = UserRepository(db)
    otp_repo = OTPRepository(db)
    
    # Find user by email
    user = await user_repo.get_by_email(request.email)
    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "If the email exists, a reset code has been sent"}
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive"
        )
    
    # Generate OTP
    otp_manager = OTPManager()
    otp_code = otp_manager.generate_otp()
    
    # Save OTP to database
    otp_create = OTPCreate(
        user_id=user.id,
        code=otp_code,
        purpose="password_reset"
    )
    
    # Invalidate any existing password reset OTPs for this user
    await otp_repo.invalidate_user_otps(user.id, "password_reset")
    
    # Create new OTP
    otp = await otp_repo.create(otp_create)
    
    # Send OTP via email
    email_service = EmailService()
    await email_service.send_password_reset_otp(
        to_email=user.email,
        user_name=user.full_name or user.username,
        otp_code=otp_code
    )
    
    # Publish password reset requested event
    reset_event = PasswordResetRequestedEvent({
        "user_id": user.id,
        "email": user.email,
        "otp_id": otp.id,
        "request_ip": "unknown",  # TODO: Get from request
    })
    
    # TODO: Publish event to Redis stream
    
    return {"message": "If the email exists, a reset code has been sent"}


@router.post("/reset-password")
async def reset_password(
    request: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Reset password using OTP verification."""
    user_repo = UserRepository(db)
    otp_repo = OTPRepository(db)
    
    # Find user by email
    user = await user_repo.get_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or OTP"
        )
    
    # Verify OTP
    otp_manager = OTPManager()
    is_valid = await otp_manager.verify_otp(
        user_id=user.id,
        otp_code=request.otp_code,
        purpose="password_reset",
        db=db
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    # Update password
    hashed_password = security.get_password_hash(request.new_password)
    user.hashed_password = hashed_password
    
    await db.commit()
    await db.refresh(user)
    
    # Invalidate all OTPs for this user
    await otp_repo.invalidate_user_otps(user.id, "password_reset")
    
    # Publish password changed event
    password_event = PasswordChangedEvent({
        "user_id": user.id,
        "email": user.email,
        "change_method": "otp_reset",
        "change_ip": "unknown",  # TODO: Get from request
    })
    
    # TODO: Publish event to Redis stream
    
    return {"message": "Password reset successfully"}


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Change password for authenticated user."""
    # Verify current password
    if not security.verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    hashed_password = security.get_password_hash(request.new_password)
    current_user.hashed_password = hashed_password
    
    await db.commit()
    await db.refresh(current_user)
    
    # Publish password changed event
    password_event = PasswordChangedEvent({
        "user_id": current_user.id,
        "email": current_user.email,
        "change_method": "authenticated_change",
        "change_ip": "unknown",  # TODO: Get from request
    })
    
    # TODO: Publish event to Redis stream
    
    return {"message": "Password changed successfully"}


@router.post("/generate-otp")
async def generate_otp(
    request: OTPRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Generate OTP for various purposes."""
    user_repo = UserRepository(db)
    otp_repo = OTPRepository(db)
    
    # Find user by email
    user = await user_repo.get_by_email(request.email)
    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "If the email exists, an OTP has been sent"}
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive"
        )
    
    # Generate OTP
    otp_manager = OTPManager()
    otp_code = otp_manager.generate_otp()
    
    # Save OTP to database
    otp_create = OTPCreate(
        user_id=user.id,
        code=otp_code,
        purpose=request.purpose
    )
    
    # Invalidate any existing OTPs for this user and purpose
    await otp_repo.invalidate_user_otps(user.id, request.purpose)
    
    # Create new OTP
    otp = await otp_repo.create(otp_create)
    
    # Send OTP via email based on purpose
    email_service = EmailService()
    
    if request.purpose == "password_reset":
        await email_service.send_password_reset_otp(
            to_email=user.email,
            user_name=user.full_name or user.username,
            otp_code=otp_code
        )
    elif request.purpose == "email_verification":
        await email_service.send_email_verification_otp(
            to_email=user.email,
            user_name=user.full_name or user.username,
            otp_code=otp_code
        )
    elif request.purpose == "two_factor":
        await email_service.send_two_factor_otp(
            to_email=user.email,
            user_name=user.full_name or user.username,
            otp_code=otp_code
        )
    else:
        await email_service.send_generic_otp(
            to_email=user.email,
            user_name=user.full_name or user.username,
            otp_code=otp_code,
            purpose=request.purpose
        )
    
    return {"message": "If the email exists, an OTP has been sent"}


@router.post("/verify-otp")
async def verify_otp(
    request: OTPVerification,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Verify OTP for various purposes."""
    user_repo = UserRepository(db)
    
    # Find user by email
    user = await user_repo.get_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or OTP"
        )
    
    # Verify OTP
    otp_manager = OTPManager()
    is_valid = await otp_manager.verify_otp(
        user_id=user.id,
        otp_code=request.otp_code,
        purpose=request.purpose,
        db=db
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    # Handle purpose-specific actions
    if request.purpose == "email_verification":
        user.is_verified = True
        await db.commit()
        await db.refresh(user)
    
    return {
        "message": "OTP verified successfully",
        "purpose": request.purpose,
        "user_id": user.id
    }