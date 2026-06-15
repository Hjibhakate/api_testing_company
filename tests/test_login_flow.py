from utils.api_client import APIClient
from utils.auth_helper import get_token

from config.config import (
    BASE_URL,
    EMAIL,
)


client = APIClient()

def test_complete_login_flow():

    # STEP 1 LOGIN
    token = get_token()

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
