from config.config import BASE_URL
from utils.api_client import APIClient
from utils.auth_helper import get_token

client = APIClient()

def save_application(job_prefix, payload):
    token = get_token()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    return client.post(
        f"{BASE_URL}/job-application/save/{job_prefix}",
        payload,
        headers=headers
    )
