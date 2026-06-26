from utils.api_client import APIClient
from utils.email_reader import get_latest_email_uid, get_otp_from_email
from utils.auth_helper import get_token as get_cached_token
from config.config import BASE_URL, EMAIL, EMAIL_PASSWORD

client = APIClient()


def send_otp():
    print("[AUTH SERVICE] Sending OTP...", flush=True)
    return client.post(
        f"{BASE_URL}/auth/send-otp",
        {"email": EMAIL}
    )


def get_otp(after_uid=None):
    print(f"[AUTH SERVICE] Reading OTP after UID: {after_uid}", flush=True)
    return get_otp_from_email(EMAIL, EMAIL_PASSWORD, after_uid=after_uid)


def login(otp):
    print("[AUTH SERVICE] Logging in with OTP...", flush=True)
    return client.post(
        f"{BASE_URL}/auth/login",
        {
            "email": EMAIL,
            "otp": otp
        }
    )


def get_token():
    print("[AUTH SERVICE] Getting auth token...", flush=True)
    return get_cached_token()


def current_user(token):
    print("[AUTH SERVICE] Fetching current user...", flush=True)
    headers = {
        "Authorization": f"Bearer {token}"
    }

    return client.get(
        f"{BASE_URL}/auth/current-user",
        headers=headers
    )
