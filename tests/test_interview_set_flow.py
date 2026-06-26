from services.interview_set_service import create_interview_plan, save_interview_set
from utils.auth_helper import get_token


def test_create_interview_set_flow():
    print("[TEST] Starting interview set creation flow.", flush=True)

    token = get_token()
    assert token is not None

    plan_response = create_interview_plan(token)
    print("[TEST] Interview plan status:", plan_response.status_code, flush=True)
    assert plan_response.status_code == 200

    plan_json = plan_response.json()
    assert plan_json.get("status") == "success"
    assert "data" in plan_json

    interview_plan = plan_json["data"]
    assert "dimensions" in interview_plan
    assert "time_allocation" in interview_plan

    save_response = save_interview_set(token, interview_plan)
    print("[TEST] Save interview set status:", save_response.status_code, flush=True)
    print("[TEST] Save interview set response:", save_response.text, flush=True)

    assert save_response.status_code in (200, 201)
    save_json = save_response.json()
    assert save_json.get("status") == "success"

    print("[TEST] Interview set created successfully.", flush=True)
