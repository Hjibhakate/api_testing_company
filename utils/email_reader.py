import imaplib
import email
import re
import time

def get_otp_from_email(email_id, password):

    print("Waiting for OTP email...")
    time.sleep(30)  # wait for email delivery

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_id, password)
    mail.select("inbox")

    status, messages = mail.search(None, "ALL")

    mail_ids = messages[0].split()

    # check last 10 emails instead of only last 1
    latest_emails = mail_ids[-10:]

    for mail_id in reversed(latest_emails):

        status, msg_data = mail.fetch(mail_id, "(RFC822)")

        raw_email = msg_data[0][1]

        msg = email.message_from_bytes(raw_email)

        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode(errors="ignore")
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        # 🔥 extract ALL 4-6 digit numbers
        otps = re.findall(r"\b\d{4,6}\b", body)

        print("Email Body Preview:", body[:200])
        print("Numbers Found:", otps)

        # pick first valid OTP (not 000000)
        for otp in otps:
            if otp != "000000":
                print("FINAL OTP:", otp)
                return otp

    return None