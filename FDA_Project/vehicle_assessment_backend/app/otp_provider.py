import os
import smtplib
import uuid
from dataclasses import dataclass
from email.mime.text import MIMEText

from app.secrets import get_secret


@dataclass
class OtpSendResult:
    provider: str
    provider_message_id: str
    status: str
    attempts: int
    error_message: str = ""


class OtpProvider:
    provider_name = "unknown"

    def send_otp(self, email: str, otp_code: str) -> OtpSendResult:
        raise NotImplementedError


class ConsoleOtpProvider(OtpProvider):
    provider_name = "console"

    def send_otp(self, email: str, otp_code: str) -> OtpSendResult:
        print(f"OTP for {email}: {otp_code}")
        return OtpSendResult(
            provider=self.provider_name,
            provider_message_id=f"console-{uuid.uuid4().hex}",
            status="sent",
            attempts=1,
        )


class SmtpOtpProvider(OtpProvider):
    provider_name = "smtp"

    def __init__(self, host: str, port: int, username: str, password: str, sender: str, max_retries: int = 3):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender
        self.max_retries = max(1, max_retries)

    def send_otp(self, email: str, otp_code: str) -> OtpSendResult:
        msg = MIMEText(f"Your Vahannetra OTP is: {otp_code}. It expires in 10 minutes.")
        msg["Subject"] = "Vahannetra OTP Verification"
        msg["From"] = self.sender
        msg["To"] = email

        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            try:
                with smtplib.SMTP(self.host, self.port, timeout=10) as client:
                    client.starttls()
                    client.login(self.username, self.password)
                    client.sendmail(self.sender, [email], msg.as_string())
                return OtpSendResult(
                    provider=self.provider_name,
                    provider_message_id=f"smtp-{uuid.uuid4().hex}",
                    status="sent",
                    attempts=attempt,
                )
            except (smtplib.SMTPException, OSError) as error:
                last_error = str(error)

        return OtpSendResult(
            provider=self.provider_name,
            provider_message_id=f"smtp-{uuid.uuid4().hex}",
            status="failed",
            attempts=self.max_retries,
            error_message=last_error,
        )


def get_otp_provider() -> OtpProvider:
    host = get_secret("OTP_SMTP_HOST")
    username = get_secret("OTP_SMTP_USERNAME")
    password = get_secret("OTP_SMTP_PASSWORD")
    sender = get_secret("OTP_SMTP_SENDER")
    port = int(os.getenv("OTP_SMTP_PORT", "587"))
    max_retries = int(os.getenv("OTP_MAX_RETRIES", "3"))

    if host and username and password and sender:
        return SmtpOtpProvider(
            host=host,
            port=port,
            username=username,
            password=password,
            sender=sender,
            max_retries=max_retries,
        )
    return ConsoleOtpProvider()
