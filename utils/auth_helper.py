from utils.api_client import APIClient
from utils.email_reader import get_latest_email_uid, get_otp_from_email
from config.config import BASE_URL, EMAIL, EMAIL_PASSWORD
import time

client = APIClient()
_TOKEN = None


def _read_otp(latest_uid):
    print("[AUTH] Waiting for a new OTP email...", flush=True)
    otp = get_otp_from_email(
        EMAIL,
        EMAIL_PASSWORD,
        max_wait_seconds=30,
        poll_interval_seconds=5,
        after_uid=latest_uid,
    )
    if otp is not None:
        print("[AUTH] New OTP email found.", flush=True)
        return otp

    # The API can return success inside a resend window without delivering
    # another email. In that case the latest inbox OTP may still be active.
    print("[AUTH] No new OTP found. Trying the latest existing OTP once...", flush=True)
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
        print("[AUTH] Using cached token.", flush=True)
        return _TOKEN

    last_error = None

    for attempt in range(2):
        print(f"[AUTH] Login attempt {attempt + 1}/2 started.", flush=True)

        # 1. send otp
        latest_uid = get_latest_email_uid(EMAIL, EMAIL_PASSWORD)
        print(f"[AUTH] Latest email UID before sending OTP: {latest_uid}", flush=True)
        send_response = client.post(f"{BASE_URL}/auth/send-otp", {"email": EMAIL})
        if send_response.status_code != 201:
            raise Exception(f"Send OTP failed: {send_response.text}")
        print("[AUTH] OTP send request accepted.", flush=True)

        # 2. wait + read otp
        otp = _read_otp(latest_uid)
        if otp is None:
            last_error = "OTP email was not received in time"
            print("[AUTH] OTP not received. Waiting before retry...", flush=True)
            time.sleep(65)
            continue

        # 3. login
        print("[AUTH] OTP received. Logging in...", flush=True)
        response = client.post(
            f"{BASE_URL}/auth/login",
            {"email": EMAIL, "otp": otp}
        )

        json_data = response.json()
        if "data" in json_data:
            _TOKEN = json_data["data"]["token"]
            print("[AUTH] Login successful. Token cached.", flush=True)
            return _TOKEN

        last_error = json_data
        print(f"[AUTH] Login response did not include token: {last_error}", flush=True)
        if attempt == 0:
            print("[AUTH] Waiting before retry...", flush=True)
            time.sleep(65)

    raise Exception(f"Login failed: {last_error}")
