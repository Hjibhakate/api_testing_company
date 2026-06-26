from datetime import datetime
from zoneinfo import ZoneInfo

from config.config import BASE_URL
from test_data.test_data import COMPANY_ID
from utils.api_client import APIClient


client = APIClient()


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}",
    }


def get_interview_set_candidates(token, interview_set_code):
    print(f"[INVITE] Fetching candidates for {interview_set_code}...", flush=True)
    return client.get(
        f"{BASE_URL}/interview-sets/{COMPANY_ID}/{interview_set_code}/candidates",
        headers=auth_headers(token),
        timeout=120,
    )


def build_invite_candidates_payload(candidates):
    return {
        "candidates": candidates,
    }


def find_invitation_link(response_json):
    data = response_json.get("data", response_json)

    def walk(value):
        if isinstance(value, dict):
            link = value.get("invitation_link")
            if isinstance(link, str) and link:
                return link

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


def build_outlook_invite_payload(email, interview_set_code, title, meeting_link):
    timezone = "Asia/Kolkata"
    today = datetime.now(ZoneInfo(timezone)).date().isoformat()
    description = (
        "Interview Schedule\n"
        f"Date: {datetime.now(ZoneInfo(timezone)).strftime('%d %b %Y')} ({timezone})\n\n"
        f"Job Role: {title}\n\n"
        "Your interview link:\n"
        f"{meeting_link}"
    )

    return {
        "to": [email],
        "optionalTo": [],
        "subject": f"Interview - {title}",
        "description": description,
        "interviewSetOrganizationId": COMPANY_ID,
        "interviewSetPrefix": interview_set_code,
        "isAllDay": True,
        "isOnlineMeeting": False,
        "jobRole": title,
        "meetingLink": meeting_link,
        "showAsTentative": False,
        "startDate": today,
        "timeZone": timezone,
    }


def invite_candidates(token, interview_set_code, candidates):
    emails = [candidate["email"] for candidate in candidates]
    print(
        f"[INVITE] Inviting {len(candidates)} candidate(s) for {interview_set_code}: "
        f"{', '.join(emails)}",
        flush=True,
    )
    return client.post(
        f"{BASE_URL}/interview-sets/{COMPANY_ID}/{interview_set_code}/invite-candidates",
        build_invite_candidates_payload(candidates),
        headers=auth_headers(token),
        timeout=120,
    )


def send_outlook_invite(token, interview_set_code, email, title, meeting_link):
    print(f"[INVITE] Sending Outlook invite to {email}...", flush=True)
    return client.post(
        f"{BASE_URL}/integrations/outlook/invite",
        build_outlook_invite_payload(email, interview_set_code, title, meeting_link),
        headers=auth_headers(token),
        timeout=120,
    )
