"""
Celery task handlers for background processing of events and notifications.
Handles email sending, inter-service communication, and other async operations.
"""

import asyncio
from typing import Dict, Any, List
from celery import Task
from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.email import EmailService
from app.services.inter_service import InterServiceClient
import logging

logger = logging.getLogger(__name__)


class AsyncTask(Task):
    """Base task class for async operations."""

    def __call__(self, *args, **kwargs):
        """Execute async task in event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.run_async(*args, **kwargs))
        finally:
            loop.close()

    async def run_async(self, *args, **kwargs):
        """Override this method in subclasses."""
        raise NotImplementedError


@celery_app.task(bind=True, base=AsyncTask, name="send_email_task")
async def send_email_task(
    self, to_email: str, subject: str, template_name: str, context: Dict[str, Any]
):
    """
    Send email using async email service.

    Args:
        to_email: Recipient email address
        subject: Email subject
        template_name: Email template name
        context: Template context variables
    """
    try:
        email_service = EmailService()
        await email_service.send_email(
            to_email=to_email,
            subject=subject,
            template_name=template_name,
            context=context,
        )
        logger.info(f"Email sent successfully to {to_email}")

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, base=AsyncTask, name="send_otp_task")
async def send_otp_task(self, email: str, otp_code: str, purpose: str):
    """
    Send OTP email to user.

    Args:
        email: User email address
        otp_code: OTP code
        purpose: OTP purpose (password_reset, email_verification, etc.)
    """
    try:
        email_service = EmailService()

        # Determine template and subject based on purpose
        template_map = {
            "password_reset": {
                "template": "password_reset_otp.html",
                "subject": "Password Reset Code",
            },
            "email_verification": {
                "template": "email_verification_otp.html",
                "subject": "Email Verification Code",
            },
            "two_factor": {
                "template": "two_factor_otp.html",
                "subject": "Two-Factor Authentication Code",
            },
        }

        template_info = template_map.get(
            purpose, {"template": "generic_otp.html", "subject": "Verification Code"}
        )

        await email_service.send_email(
            to_email=email,
            subject=template_info["subject"],
            template_name=template_info["template"],
            context={
                "otp_code": otp_code,
                "purpose": purpose,
                "expires_in": settings.otp_expire_minutes,
            },
        )

        logger.info(f"OTP email sent successfully to {email} for {purpose}")

    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        raise self.retry(exc=e, countdown=30, max_retries=3)


@celery_app.task(bind=True, base=AsyncTask, name="process_user_created_event")
async def process_user_created_event(self, user_data: Dict[str, Any]):
    """
    Process user created event and notify other services.

    Args:
        user_data: User information to broadcast
    """
    try:
        from app.services.inter_service import user_validation_service
        
        # Notify other services
        await user_validation_service.notify_user_created(user_data)

        # Send welcome email
        email_service = EmailService()
        await email_service.send_welcome_email(
            to_email=user_data["email"],
            full_name=user_data.get("full_name", user_data["username"]),
            username=user_data["username"]
        )

        logger.info(f"User creation event processed for user {user_data['id']}")

    except Exception as e:
        logger.error(f"Failed to process user creation event: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, base=AsyncTask, name="process_user_updated_event")
async def process_user_updated_event(self, user_data: Dict[str, Any]):
    """
    Process user updated event and notify other services.

    Args:
        user_data: Updated user information
    """
    try:
        from app.services.inter_service import user_validation_service
        
        await user_validation_service.notify_user_updated(user_data["id"], user_data)

        logger.info(f"User update event processed for user {user_data['id']}")

    except Exception as e:
        logger.error(f"Failed to process user update event: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, base=AsyncTask, name="process_user_deleted_event")
async def process_user_deleted_event(self, user_data: Dict[str, Any]):
    """
    Process user deleted event and notify other services.

    Args:
        user_data: Deleted user information
    """
    try:
        from app.services.inter_service import user_validation_service
        
        await user_validation_service.notify_user_deleted(user_data["user_id"])

        logger.info(f"User deletion event processed for user {user_data['user_id']}")

    except Exception as e:
        logger.error(f"Failed to process user deletion event: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, base=AsyncTask, name="cleanup_expired_otps_task")
async def cleanup_expired_otps_task(self):
    """
    Cleanup expired OTP codes from database.
    This task should be scheduled to run periodically.
    """
    try:
        from app.db.session import get_async_session
        from app.services.otp_manager import OTPManager
        
        async with get_async_session() as db:
            otp_manager = OTPManager()
            deleted_count = await otp_manager.cleanup_expired_otps(db)
            
        logger.info(f"OTP cleanup task executed, deleted {deleted_count} expired OTPs")
        return deleted_count

    except Exception as e:
        logger.error(f"Failed to cleanup expired OTPs: {str(e)}")
        raise self.retry(exc=e, countdown=300, max_retries=3)


@celery_app.task(bind=True, name="sync_user_permissions")
def sync_user_permissions_task(self, user_id: int):
    """
    Sync user permissions across services.

    Args:
        user_id: User ID to sync permissions for
    """
    try:
        # Implementation would fetch user permissions and sync with other services
        logger.info(f"Permission sync task executed for user {user_id}")

    except Exception as e:
        logger.error(f"Failed to sync permissions for user {user_id}: {str(e)}")
        raise self.retry(exc=e, countdown=120, max_retries=3)
