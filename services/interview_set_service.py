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
    draft.pop("aiVoiceGender", None)
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


def find_interview_set_code(response_json):
    data = response_json.get("data", response_json)
    keys = (
        "setPrefix",
        "interview_set_code",
        "interviewSetCode",
        "interviewSetPrefix",
        "prefix",
        "slug",
        "code",
    )

    def walk(value):
        if isinstance(value, dict):
            for key in keys:
                found = value.get(key)
                if isinstance(found, str) and found:
                    if found.lower() in {"technical", "behavioral", "bei"}:
                        continue
                    return found

            for child in value.values():
                found = walk(child)
                if found:
                    return found

        if isinstance(value, list):
            for child in value:
                found = walk(child)
                if found:
                    return found

        return None

    return walk(data)
