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


def run_job_aggregator(job_prefix, token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    return client.post(
        f"{BASE_URL}/aggregator/{job_prefix}",
        None,
        headers=headers
    )


def publish_job(job_prefix, payload, token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    return client.patch(
        f"{BASE_URL}/jobs/{job_prefix}",
        payload,
        headers=headers
    )

