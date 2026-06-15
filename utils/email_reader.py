import imaplib
import email
from email.utils import parsedate_to_datetime
import re
import time


def get_latest_email_uid(email_id, password):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    try:
        mail.login(email_id, password)
        mail.select("inbox")

        status, messages = mail.uid("search", None, "ALL")
        if status != "OK" or not messages or not messages[0]:
            return None

        return int(messages[0].split()[-1])
    finally:
        try:
            mail.logout()
        except Exception:
            pass


def get_otp_from_email(
    email_id,
    password,
    max_wait_seconds: int = 120,
    poll_interval_seconds: int = 5,
    since_timestamp: float | None = None,
    after_uid: int | None = None,
):
    """Fetch OTP from inbox with polling.

    Assumes the email body contains the OTP as the last 4-6 digit number.
    """

    print("Waiting for OTP email...")

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_id, password)
    mail.select("inbox")

    deadline = time.time() + max_wait_seconds

    while time.time() < deadline:
        if after_uid is None:
            status, messages = mail.uid("search", None, "ALL")
        else:
            status, messages = mail.uid("search", None, f"UID {after_uid + 1}:*")

        if status != "OK" or not messages or not messages[0]:
            time.sleep(poll_interval_seconds)
            continue

        mail_ids = messages[0].split()
        if after_uid is not None:
            mail_ids = [mail_id for mail_id in mail_ids if int(mail_id) > after_uid]
            if not mail_ids:
                time.sleep(poll_interval_seconds)
                continue

        latest_emails = mail_ids[-10:]

        for mail_id in reversed(latest_emails):
            status, msg_data = mail.uid("fetch", mail_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            if since_timestamp is not None:
                date_header = msg.get("Date")
                if not date_header:
                    continue

                try:
                    received_at = parsedate_to_datetime(date_header).timestamp()
                except (TypeError, ValueError, OverflowError):
                    continue

                if received_at < since_timestamp:
                    continue

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() in ("text/plain", "text/html"):
                        body += part.get_payload(decode=True).decode(errors="ignore")
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            otps = re.findall(r"\b\d{4,6}\b", body)
            otps = [o for o in otps if o and o != "000000"]

            if otps:
                # Prefer OTPs that look like they are repeated in the email.
                from collections import Counter
                counts = Counter(otps)

                # Prefer 6-digit OTPs, otherwise 4-digit.
                def sort_key(x: str):
                    # higher count first
                    return (-counts[x], -len(x))

                otp = sorted(set(otps), key=sort_key)[0]
                print("FINAL OTP:", otp)
                try:
                    mail.logout()
                except Exception:
                    pass
                return otp

        time.sleep(poll_interval_seconds)

    try:
        mail.logout()
    except Exception:
        pass

    return None
