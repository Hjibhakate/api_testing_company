from utils.api_client import APIClient
from utils.email_reader import get_latest_email_uid, get_otp_from_email
from utils.auth_helper import get_token as get_cached_token
from config.config import BASE_URL, EMAIL, EMAIL_PASSWORD

client = APIClient()


def send_otp():
    return client.post(
        f"{BASE_URL}/auth/send-otp",
        {"email": EMAIL}
    )


def get_otp(after_uid=None):
    return get_otp_from_email(EMAIL, EMAIL_PASSWORD, after_uid=after_uid)


def login(otp):
    return client.post(
        f"{BASE_URL}/auth/login",
        {
            "email": EMAIL,
            "otp": otp
        }
    )


def get_token():
    return get_cached_token()


def current_user(token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    return client.get(
        f"{BASE_URL}/auth/current-user",
        headers=headers
    )
