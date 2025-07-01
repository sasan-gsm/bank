"""Email service for sending OTPs, notifications, and other email communications."""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from jinja2 import Environment, DictLoader
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Async email service using SMTP."""

    def __init__(self):
        """Initialize email service with SMTP configuration."""
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.smtp_use_tls = settings.smtp_use_tls

        # Email templates
        self.templates = {
            "password_reset_otp": """
            <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Hello {{ user_name }},</p>
                <p>You have requested to reset your password. Please use the following OTP code:</p>
                <h3 style="color: #007bff; font-family: monospace;">{{ otp_code }}</h3>
                <p>This code will expire in {{ expiry_minutes }} minutes.</p>
                <p>If you did not request this password reset, please ignore this email.</p>
                <br>
                <p>Best regards,<br>Banking Auth Service</p>
            </body>
            </html>
            """,
            "email_verification_otp": """
            <html>
            <body>
                <h2>Email Verification</h2>
                <p>Hello {{ user_name }},</p>
                <p>Please verify your email address using the following OTP code:</p>
                <h3 style="color: #28a745; font-family: monospace;">{{ otp_code }}</h3>
                <p>This code will expire in {{ expiry_minutes }} minutes.</p>
                <br>
                <p>Best regards,<br>Banking Auth Service</p>
            </body>
            </html>
            """,
            "two_factor_otp": """
            <html>
            <body>
                <h2>Two-Factor Authentication</h2>
                <p>Hello {{ user_name }},</p>
                <p>Your two-factor authentication code is:</p>
                <h3 style="color: #ffc107; font-family: monospace;">{{ otp_code }}</h3>
                <p>This code will expire in {{ expiry_minutes }} minutes.</p>
                <p>If you did not request this code, please contact support immediately.</p>
                <br>
                <p>Best regards,<br>Banking Auth Service</p>
            </body>
            </html>
            """,
            "generic_otp": """
            <html>
            <body>
                <h2>Verification Code</h2>
                <p>Hello {{ user_name }},</p>
                <p>Your verification code for {{ purpose }} is:</p>
                <h3 style="color: #6c757d; font-family: monospace;">{{ otp_code }}</h3>
                <p>This code will expire in {{ expiry_minutes }} minutes.</p>
                <br>
                <p>Best regards,<br>Banking Auth Service</p>
            </body>
            </html>
            """,
            "welcome_email": """
            <html>
            <body>
                <h2>Welcome to Banking Auth Service</h2>
                <p>Hello {{ user_name }},</p>
                <p>Welcome to our banking platform! Your account has been successfully created.</p>
                <p>Account Details:</p>
                <ul>
                    <li>Username: {{ username }}</li>
                    <li>Email: {{ email }}</li>
                    <li>Registration Date: {{ registration_date }}</li>
                </ul>
                <p>Please verify your email address to activate all features.</p>
                <br>
                <p>Best regards,<br>Banking Auth Service</p>
            </body>
            </html>
            """,
        }

        # Initialize Jinja2 environment
        self.jinja_env = Environment(loader=DictLoader(self.templates))

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send email using SMTP."""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.smtp_username or "noreply@bankingauth.com"
            message["To"] = to_email

            # Add text part if provided
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                use_tls=self.smtp_use_tls,
            )

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_password_reset_otp(
        self, to_email: str, user_name: str, otp_code: str
    ) -> bool:
        """Send password reset OTP email."""
        template = self.jinja_env.get_template("password_reset_otp")
        html_content = template.render(
            user_name=user_name,
            otp_code=otp_code,
            expiry_minutes=settings.otp_expire_minutes,
        )

        return await self._send_email(
            to_email=to_email,
            subject="Password Reset - Banking Auth Service",
            html_content=html_content,
        )

    async def send_email_verification_otp(
        self, to_email: str, user_name: str, otp_code: str
    ) -> bool:
        """Send email verification OTP."""
        template = self.jinja_env.get_template("email_verification_otp")
        html_content = template.render(
            user_name=user_name,
            otp_code=otp_code,
            expiry_minutes=settings.otp_expire_minutes,
        )

        return await self._send_email(
            to_email=to_email,
            subject="Email Verification - Banking Auth Service",
            html_content=html_content,
        )

    async def send_two_factor_otp(
        self, to_email: str, user_name: str, otp_code: str
    ) -> bool:
        """Send two-factor authentication OTP."""
        template = self.jinja_env.get_template("two_factor_otp")
        html_content = template.render(
            user_name=user_name,
            otp_code=otp_code,
            expiry_minutes=settings.otp_expire_minutes,
        )

        return await self._send_email(
            to_email=to_email,
            subject="Two-Factor Authentication - Banking Auth Service",
            html_content=html_content,
        )

    async def send_generic_otp(
        self, to_email: str, user_name: str, otp_code: str, purpose: str
    ) -> bool:
        """Send generic OTP email."""
        template = self.jinja_env.get_template("generic_otp")
        html_content = template.render(
            user_name=user_name,
            otp_code=otp_code,
            purpose=purpose.replace("_", " ").title(),
            expiry_minutes=settings.otp_expire_minutes,
        )

        return await self._send_email(
            to_email=to_email,
            subject=f"Verification Code - {purpose.replace('_', ' ').title()}",
            html_content=html_content,
        )

    async def send_welcome_email(
        self, to_email: str, user_name: str, username: str, registration_date: str
    ) -> bool:
        """Send welcome email to new users."""
        template = self.jinja_env.get_template("welcome_email")
        html_content = template.render(
            user_name=user_name,
            username=username,
            email=to_email,
            registration_date=registration_date,
        )

        return await self._send_email(
            to_email=to_email,
            subject="Welcome to Banking Auth Service",
            html_content=html_content,
        )

    async def send_email(
        self, to_email: str, subject: str, template_name: str, context: Dict[str, Any]
    ) -> bool:
        """Send email using a template."""
        try:
            template = self.jinja_env.get_template(template_name)
            html_content = template.render(**context)

            return await self._send_email(
                to_email=to_email, subject=subject, html_content=html_content
            )
        except Exception as e:
            logger.error(f"Failed to send templated email: {str(e)}")
            return False
