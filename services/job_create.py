from utils.api_client import APIClient
from config.config import BASE_URL

client = APIClient()


def create_job(payload, token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    return client.post(
        f"{BASE_URL}/jobs",
        payload,
        headers=headers
    )
