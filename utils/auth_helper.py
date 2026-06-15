from utils.api_client import APIClient
from utils.email_reader import get_latest_email_uid, get_otp_from_email
from config.config import BASE_URL, EMAIL, EMAIL_PASSWORD
import time

client = APIClient()
_TOKEN = None


def _read_otp(latest_uid):
    otp = get_otp_from_email(
        EMAIL,
        EMAIL_PASSWORD,
        max_wait_seconds=30,
        poll_interval_seconds=5,
        after_uid=latest_uid,
    )
    if otp is not None:
        return otp

    # The API can return success inside a resend window without delivering
    # another email. In that case the latest inbox OTP may still be active.
    fallback_uid = latest_uid - 1 if latest_uid is not None and latest_uid > 0 else None
    return get_otp_from_email(
        EMAIL,
        EMAIL_PASSWORD,
        max_wait_seconds=5,
        poll_interval_seconds=1,
        after_uid=fallback_uid,
    )


def get_token():
    global _TOKEN
    if _TOKEN is not None:
        return _TOKEN

    last_error = None

    for attempt in range(2):
        # 1. send otp
        latest_uid = get_latest_email_uid(EMAIL, EMAIL_PASSWORD)
        send_response = client.post(f"{BASE_URL}/auth/send-otp", {"email": EMAIL})
        if send_response.status_code != 201:
            raise Exception(f"Send OTP failed: {send_response.text}")

        # 2. wait + read otp
        otp = _read_otp(latest_uid)
        if otp is None:
            last_error = "OTP email was not received in time"
            time.sleep(65)
            continue

        # 3. login
        response = client.post(
            f"{BASE_URL}/auth/login",
            {"email": EMAIL, "otp": otp}
        )

        json_data = response.json()
        if "data" in json_data:
            _TOKEN = json_data["data"]["token"]
            return _TOKEN

        last_error = json_data
        if attempt == 0:
            time.sleep(65)

    raise Exception(f"Login failed: {last_error}")
