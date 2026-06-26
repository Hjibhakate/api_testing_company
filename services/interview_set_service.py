from copy import deepcopy

from config.config import BASE_URL
from test_data.test_data import COMPANY_ID, INTERVIEW_SET_DRAFT
from utils.api_client import APIClient


client = APIClient()


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}",
    }


def build_interview_plan_payload(draft=None):
    if draft is None:
        draft = INTERVIEW_SET_DRAFT

    return {
        "companyId": COMPANY_ID,
        "prefix": "",
        "draft": deepcopy(draft),
    }


def build_save_payload(interview_plan, draft=None):
    if draft is None:
        draft = INTERVIEW_SET_DRAFT

    draft = deepcopy(draft)
    draft["interview_plan"] = interview_plan

    return draft


def create_interview_plan(token, draft=None):
    title = (draft or INTERVIEW_SET_DRAFT).get("title", "Interview Set")
    print(f"[INTERVIEW SET] Creating interview plan for {title}...", flush=True)
    return client.post(
        f"{BASE_URL}/interview-sets/interview-plan",
        build_interview_plan_payload(draft),
        headers=auth_headers(token),
        timeout=120,
    )


def save_interview_set(token, interview_plan, draft=None):
    title = (draft or INTERVIEW_SET_DRAFT).get("title", "Interview Set")
    print(f"[INTERVIEW SET] Saving interview set for {title}...", flush=True)
    return client.post(
        f"{BASE_URL}/interview-sets/{COMPANY_ID}/save",
        build_save_payload(interview_plan, draft),
        headers=auth_headers(token),
        timeout=120,
    )
