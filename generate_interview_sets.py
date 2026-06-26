from copy import deepcopy

from services.invite_service import (
    find_invitation_link,
    get_interview_set_candidates,
    invite_candidates,
    send_outlook_invite,
)
from services.interview_set_service import create_interview_plan, save_interview_set
from services.interview_set_service import find_interview_set_code
from test_data.test_data import (
    AI_AVATAR_FEMALE_URL,
    AI_AVATAR_MALE_URL,
    AI_VOICE_FEMALE_ID,
    AI_VOICE_MALE_ID,
    INTERVIEW_SET_DRAFT,
)
from utils.auth_helper import get_token
from utils.openrouter_client import generate_job_roles, verify_interview_plan


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


def ask_choice(question, choices, default):
    normalized_choices = {choice.upper(): choice.upper() for choice in choices}

    while True:
        answer = ask_text(question, default).upper()
        if answer in normalized_choices:
            return normalized_choices[answer]

        print(f"Please choose one of: {', '.join(choices)}", flush=True)


def get_ai_avatar_url(ai_avatar_gender):
    if ai_avatar_gender == "MALE":
        return AI_AVATAR_MALE_URL

    return AI_AVATAR_FEMALE_URL


def get_ai_voice_id(ai_voice_gender):
    if ai_voice_gender == "MALE":
        return AI_VOICE_MALE_ID

    return AI_VOICE_FEMALE_ID


def build_draft(
    role_data,
    experience_range,
    question_mode=None,
    duration=None,
    ai_voice_gender=None,
    ai_avatar_gender=None,
):
    draft = deepcopy(INTERVIEW_SET_DRAFT)
    draft.update(role_data)
    draft["title"] = role_data["title"]
    draft["role"] = role_data.get("role", role_data["title"])
    draft["experience_level"] = experience_range
    draft["question_mode"] = question_mode or role_data.get("question_mode", draft["question_mode"])
    draft["duration"] = int(duration or role_data.get("duration", draft["duration"]))
    if ai_voice_gender:
        draft["aiVoice"] = get_ai_voice_id(ai_voice_gender)
    if ai_avatar_gender:
        draft["aiAvatar"] = get_ai_avatar_url(ai_avatar_gender)
    print(f"[DRAFT] AI voice: {draft['aiVoice']}", flush=True)
    print(f"[DRAFT] AI avatar: {draft['aiAvatar']}", flush=True)
    return draft


def create_one_interview_set(
    token,
    draft,
    should_cancel=None,
    review_callback=None,
):
    if should_cancel is not None and should_cancel():
        print("[CREATE] Cancel requested. Skipping next interview set.", flush=True)
        return False

    plan_response = create_interview_plan(token, draft)
    if plan_response.status_code != 200:
        print("[CREATE] Interview plan failed:", plan_response.text, flush=True)
        return False

    plan_json = plan_response.json()
    if plan_json.get("status") != "success" or "data" not in plan_json:
        print("[CREATE] Interview plan response is invalid:", plan_response.text, flush=True)
        return False

    interview_plan = plan_json["data"]
    review = verify_interview_plan(
        draft["role"],
        draft["experience_level"],
        draft["duration"],
        draft["question_mode"],
        interview_plan,
    )
    print(
        f"[VERIFY] {draft['title']} plan rating: {review['rating']}/10 "
        f"({review['verdict']})",
        flush=True,
    )
    if review["reason"]:
        print(f"[VERIFY] Reason: {review['reason']}", flush=True)

    factor_scores = review.get("factor_scores") or {}
    factor_labels = {
        "role_relevance": "Role relevance",
        "experience_fit": "Experience fit",
        "skill_coverage": "Skill coverage",
        "time_allocation": "Time allocation",
        "specificity": "Specificity",
    }
    for factor_key, factor_label in factor_labels.items():
        factor = factor_scores.get(factor_key) or {}
        if factor:
            print(
                f"[VERIFY] {factor_label}: {factor.get('score', '-')}/10 - "
                f"{factor.get('reason', 'No detail returned.')}",
                flush=True,
            )

    weak_topics = review.get("missing_or_weak_topics") or []
    if weak_topics:
        print(f"[VERIFY] Missing/weak topics: {', '.join(weak_topics)}", flush=True)

    if review_callback is not None:
        review_callback(draft, review)

    if should_cancel is not None and should_cancel():
        print("[CREATE] Cancel requested after verification. Save skipped.", flush=True)
        return False

    save_response = save_interview_set(token, interview_plan, draft)
    if save_response.status_code not in (200, 201):
        print("[CREATE] Save failed:", save_response.text, flush=True)
        return False

    save_json = save_response.json()
    if save_json.get("status") != "success":
        print("[CREATE] Save response is not success:", save_response.text, flush=True)
        return False

    print(f"[CREATE] Created interview set: {draft['title']}", flush=True)
    return {
        "title": draft["title"],
        "code": find_interview_set_code(save_json),
        "response": save_json,
    }


def invite_candidate_flow(token, interview_set):
    code = interview_set.get("code")
    title = interview_set.get("title", "Interview Set")
    if not code:
        print(f"[INVITE] Could not find interview set code for {title}. Invite skipped.", flush=True)
        return False

    should_invite = ask_choice(
        f"Do you want to invite a candidate for {title} ({code})? YES or NO",
        ("YES", "NO"),
        "NO",
    )
    if should_invite != "YES":
        print(f"[INVITE] Invite skipped for {title}.", flush=True)
        return False

    email = ask_text("Enter candidate email")
    if not email:
        print("[INVITE] No email entered. Invite skipped.", flush=True)
        return False

    first_name = ask_text("Enter candidate first name")
    last_name = ask_text("Enter candidate last name")
    if not first_name or not last_name:
        print("[INVITE] First name and last name are required. Invite skipped.", flush=True)
        return False

    return send_candidate_invite(token, interview_set, email, first_name, last_name)


def send_candidate_invite(token, interview_set, email, first_name, last_name):
    code = interview_set.get("code")
    title = interview_set.get("title", "Interview Set")
    if not code:
        print(f"[INVITE] Could not find interview set code for {title}. Invite skipped.", flush=True)
        return False

    candidates_response = get_interview_set_candidates(token, code)
    if candidates_response.status_code != 200:
        print("[INVITE] Candidate fetch failed:", candidates_response.text, flush=True)

    invite_response = invite_candidates(token, code, email, first_name, last_name)
    if invite_response.status_code not in (200, 201):
        print("[INVITE] Invite candidates failed:", invite_response.text, flush=True)
        return False

    invite_json = invite_response.json()
    meeting_link = find_invitation_link(invite_json)
    if not meeting_link:
        print("[INVITE] Invitation link not found. Outlook invite skipped.", flush=True)
        return False

    outlook_response = send_outlook_invite(token, code, email, title, meeting_link)
    if outlook_response.status_code not in (200, 201):
        print("[INVITE] Outlook invite failed:", outlook_response.text, flush=True)
        return False

    print(f"[INVITE] Invite sent to {email} for {title}.", flush=True)
    return True


def main():
    print("Interview Set Generator", flush=True)
    print("This will generate role drafts with OpenRouter and create interview sets.", flush=True)

    job_family = ask_text("Which type of job roles do you want to generate?", "Engineering")
    count = ask_int("How many job roles do you want to generate?", 5)
    experience_range = ask_text("What experience range do you want?", "1-2 years")
    question_mode = ask_choice(
        "Which question mode do you want? DIRECT, SCENARIO, or BEI",
        ("DIRECT", "SCENARIO", "BEI"),
        "DIRECT",
    )
    duration = ask_int("How many minutes for interview? 10, 20, 30, 45, or 60", 30)
    ai_voice_gender = ask_choice(
        "Which AI voice do you want? MALE or FEMALE",
        ("MALE", "FEMALE"),
        "FEMALE",
    )
    ai_avatar_gender = ask_choice(
        "Which AI avatar do you want? MALE or FEMALE",
        ("MALE", "FEMALE"),
        "FEMALE",
    )

    roles = generate_job_roles(job_family, count, experience_range, question_mode, duration)
    print("\nGenerated roles:", flush=True)
    for index, role in enumerate(roles, start=1):
        print(f"{index}. {role['title']} ({role.get('seniority', 'Senior')})", flush=True)

    confirm = ask_text("\nCreate interview sets for these roles? Type yes to continue", "no")
    if confirm.lower() != "yes":
        print("Cancelled.", flush=True)
        return

    token = get_token()
    success_count = 0
    invite_count = 0

    for role in roles:
        draft = build_draft(
            role,
            experience_range,
            question_mode,
            duration,
            ai_voice_gender,
            ai_avatar_gender,
        )
        print(f"\n[CREATE] Starting: {draft['title']}", flush=True)
        created_set = create_one_interview_set(token, draft)
        if created_set:
            success_count += 1
            if invite_candidate_flow(token, created_set):
                invite_count += 1

    print(f"\nFinished. Created {success_count}/{len(roles)} interview sets.", flush=True)
    print(f"Finished. Sent {invite_count} candidate invites.", flush=True)


if __name__ == "__main__":
    main()
