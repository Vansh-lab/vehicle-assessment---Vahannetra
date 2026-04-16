import os
import smtplib
from email.mime.text import MIMEText


class OtpProvider:
    def send_otp(self, email: str, otp_code: str) -> None:
        raise NotImplementedError


class ConsoleOtpProvider(OtpProvider):
    def send_otp(self, email: str, otp_code: str) -> None:
        print(f"OTP for {email}: {otp_code}")


class SmtpOtpProvider(OtpProvider):
    def __init__(self, host: str, port: int, username: str, password: str, sender: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender

    def send_otp(self, email: str, otp_code: str) -> None:
        msg = MIMEText(f"Your Vahannetra OTP is: {otp_code}. It expires in 10 minutes.")
        msg["Subject"] = "Vahannetra OTP Verification"
        msg["From"] = self.sender
        msg["To"] = email

        with smtplib.SMTP(self.host, self.port, timeout=10) as client:
            client.starttls()
            client.login(self.username, self.password)
            client.sendmail(self.sender, [email], msg.as_string())


def get_otp_provider() -> OtpProvider:
    host = os.getenv("OTP_SMTP_HOST")
    username = os.getenv("OTP_SMTP_USERNAME")
    password = os.getenv("OTP_SMTP_PASSWORD")
    sender = os.getenv("OTP_SMTP_SENDER")
    port = int(os.getenv("OTP_SMTP_PORT", "587"))

    if host and username and password and sender:
        return SmtpOtpProvider(host=host, port=port, username=username, password=password, sender=sender)
    return ConsoleOtpProvider()
