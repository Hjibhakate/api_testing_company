from utils.api_client import APIClient
from utils.email_reader import get_otp_from_email

from config.config import (
    BASE_URL,
    EMAIL,
    EMAIL_PASSWORD
)

client = APIClient()

def test_complete_login_flow():

    # STEP 1 SEND OTP

    send_otp_payload = {
        "email": EMAIL
    }

    send_otp_response = client.post(
        f"{BASE_URL}/auth/send-otp",
        send_otp_payload
    )

    print("Send OTP Status:", send_otp_response.status_code)
    print("Send OTP Response:", send_otp_response.text)

    assert send_otp_response.status_code == 201

    print("OTP Sent Successfully")

    # STEP 2 READ OTP

    otp = get_otp_from_email(
        EMAIL,
        EMAIL_PASSWORD
    )

    print("OTP =", otp)

    assert otp is not None

    # STEP 3 LOGIN

    login_payload = {
        "email": EMAIL,
        "otp": otp
    }

    login_response = client.post(
        f"{BASE_URL}/auth/login",
        login_payload
    )

    print("Login Status:", login_response.status_code)
    print("Login Response:", login_response.text)

    assert login_response.status_code == 201

    login_json = login_response.json()

    token = login_json.get("data", {}).get("token")

    print("Token:", token)

    assert token is not None

    # STEP 4 FETCH SLUG

    headers = {
        "Authorization": f"Bearer {token}"
    }

    slug_payload = {
        "email": EMAIL
    }

    slug_response = client.post(
        f"{BASE_URL}/auth/fetch-slug",
        slug_payload,
        headers
    )

    print("Fetch Slug Status:", slug_response.status_code)
    print("Fetch Slug Response:", slug_response.text)

    assert slug_response.status_code == 201

    # STEP 5 CURRENT USER

    current_user_response = client.get(
        f"{BASE_URL}/auth/current-user",
        headers
    )

    print("Current User Status:", current_user_response.status_code)
    print("Current User Response:", current_user_response.text)

    assert current_user_response.status_code == 200

    print("Login Flow Passed Successfully")