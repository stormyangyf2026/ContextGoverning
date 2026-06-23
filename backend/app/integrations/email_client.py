"""Email client — IMAP email collection."""
import email
import imaplib
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from app.config import get_settings


class EmailClient:
    """Client for collecting emails via IMAP."""

    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password

    def fetch_recent(self, mailbox: str = "INBOX", days: int = None) -> List[Dict]:
        """Fetch recent emails from the specified mailbox."""
        settings = get_settings()
        if days is None:
            days = settings.email_fetch_days

        emails = []
        try:
            mail = imaplib.IMAP4_SSL(self.host)
            mail.login(self.username, self.password)
            mail.select(mailbox)

            since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
            result, data = mail.search(None, f'(SINCE "{since}")')

            if result == "OK":
                max_fetch = settings.email_fetch_max
                for num in data[0].split()[-max_fetch:]:
                    result, msg_data = mail.fetch(num, "(RFC822)")
                    if result == "OK":
                        msg = email.message_from_bytes(msg_data[0][1])
                        emails.append({
                            "subject": msg.get("Subject", ""),
                            "from": msg.get("From", ""),
                            "to": msg.get("To", ""),
                            "date": msg.get("Date", ""),
                            "body": _get_body(msg),
                        })
            mail.close()
            mail.logout()
        except Exception:
            pass
        return emails


def _get_body(msg) -> str:
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode()
                except Exception:
                    pass
    else:
        try:
            return msg.get_payload(decode=True).decode()
        except Exception:
            pass
    return ""
