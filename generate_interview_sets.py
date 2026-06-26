from copy import deepcopy

from services.interview_set_service import create_interview_plan, save_interview_set
from test_data.test_data import INTERVIEW_SET_DRAFT
from utils.auth_helper import get_token
from utils.openrouter_client import generate_job_roles


def ask_text(question, default=None):
    suffix = f" [{default}]" if default else ""
    answer = input(f"{question}{suffix}: ").strip()
    return answer or default


def ask_int(question, default=5):
    while True:
        answer = ask_text(question, str(default))
        try:
            value = int(answer)
        except (TypeError, ValueError):
            print("Please enter a number.", flush=True)
            continue

        if value < 1:
            print("Please enter at least 1.", flush=True)
            continue

        return value


def build_draft(role_data, experience_range):
    draft = deepcopy(INTERVIEW_SET_DRAFT)
    draft.update(role_data)
    draft["title"] = role_data["title"]
    draft["role"] = role_data.get("role", role_data["title"])
    draft["experience_level"] = experience_range
    draft["duration"] = int(role_data.get("duration", draft["duration"]))
    return draft


def create_one_interview_set(token, draft):
    plan_response = create_interview_plan(token, draft)
    if plan_response.status_code != 200:
        print("[CREATE] Interview plan failed:", plan_response.text, flush=True)
        return False

    plan_json = plan_response.json()
    if plan_json.get("status") != "success" or "data" not in plan_json:
        print("[CREATE] Interview plan response is invalid:", plan_response.text, flush=True)
        return False

    save_response = save_interview_set(token, plan_json["data"], draft)
    if save_response.status_code not in (200, 201):
        print("[CREATE] Save failed:", save_response.text, flush=True)
        return False

    save_json = save_response.json()
    if save_json.get("status") != "success":
        print("[CREATE] Save response is not success:", save_response.text, flush=True)
        return False

    print(f"[CREATE] Created interview set: {draft['title']}", flush=True)
    return True


def main():
    print("Interview Set Generator", flush=True)
    print("This will generate role drafts with OpenRouter and create interview sets.", flush=True)

    job_family = ask_text("Which type of job roles do you want to generate?", "Engineering")
    count = ask_int("How many job roles do you want to generate?", 5)
    experience_range = ask_text("What experience range do you want?", "1-2 years")

    roles = generate_job_roles(job_family, count, experience_range)
    print("\nGenerated roles:", flush=True)
    for index, role in enumerate(roles, start=1):
        print(f"{index}. {role['title']} ({role.get('seniority', 'Senior')})", flush=True)

    confirm = ask_text("\nCreate interview sets for these roles? Type yes to continue", "no")
    if confirm.lower() != "yes":
        print("Cancelled.", flush=True)
        return

    token = get_token()
    success_count = 0

    for role in roles:
        draft = build_draft(role, experience_range)
        print(f"\n[CREATE] Starting: {draft['title']}", flush=True)
        if create_one_interview_set(token, draft):
            success_count += 1

    print(f"\nFinished. Created {success_count}/{len(roles)} interview sets.", flush=True)


if __name__ == "__main__":
    main()
