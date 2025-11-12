# utils/email_notifier.py

import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ---------- CONFIGURE THESE ----------
SENDER_EMAIL = "vasanthanjeyaraj@gmail.com"      # ✅ your Gmail
SENDER_PASSWORD = "rkrjitzfrdfipyav"            
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
# -------------------------------------

def _send_email_blocking(msg):
    """Blocking SMTP send helper (run in thread)."""
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

async def send_failure_email(error_message: str, frequency: str):
    """Send email alert when a scrape fails."""
    try:
        receiver_email = "vasanthanjt06@gmail.com"
        subject = f"❌ Scrape Failed: {frequency} | {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        body = f"""
Hello,

The Amazon scraping task for schedule '{frequency}' has failed.

Error Details:
----------------
{error_message}

Please check the logs or server for details.

Regards,
Scraper Monitoring System
        """

        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # ✅ run SMTP in background thread
        await asyncio.to_thread(_send_email_blocking, msg)

        print(f"📧 Sent failure email to {receiver_email}")

    except Exception as e:
        print(f"⚠️ Failed to send email notification: {e}")
