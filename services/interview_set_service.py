from copy import deepcopy

from config.config import BASE_URL
from test_data.test_data import COMPANY_ID, INTERVIEW_SET_DRAFT
from utils.api_client import APIClient


client = APIClient()


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}",
    }


def build_interview_plan_payload():
    return {
        "companyId": COMPANY_ID,
        "prefix": "",
        "draft": deepcopy(INTERVIEW_SET_DRAFT),
    }


def build_save_payload(interview_plan):
    draft = deepcopy(INTERVIEW_SET_DRAFT)
    draft["interview_plan"] = interview_plan

    return draft


def create_interview_plan(token):
    print("[INTERVIEW SET] Creating interview plan...", flush=True)
    return client.post(
        f"{BASE_URL}/interview-sets/interview-plan",
        build_interview_plan_payload(),
        headers=auth_headers(token),
        timeout=120,
    )


def save_interview_set(token, interview_plan):
    print("[INTERVIEW SET] Saving interview set...", flush=True)
    return client.post(
        f"{BASE_URL}/interview-sets/{COMPANY_ID}/save",
        build_save_payload(interview_plan),
        headers=auth_headers(token),
        timeout=120,
    )
