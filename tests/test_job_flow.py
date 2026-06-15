from services.job_service import generate_job_description
from services.job_create import create_job, publish_job, run_job_aggregator
from services.application_service import save_application
from utils.auth_helper import get_token

COMPANY_ID = "c2af53c8-073f-4d18-a0b2-ed5735abea45"


def test_full_job_flow():

    # STEP 1 - generate job description
    gen_payload = {
        "modelName": "AI",
        "jobRole": "QA Engineer",
        "experience": "2",
        "locations": ["Nagpur, India"],
        "employment_type": ["Full-time"],
        "work_mode": ["On-site"]
    }

    gen_response = generate_job_description(gen_payload)
    assert gen_response.status_code == 201

    print("Job Description Generated")

    # STEP 2 - create job
    generated_output = gen_response.json()["data"]["data"]["output"]
    employment_type = generated_output.get("employment_type", gen_payload["employment_type"])
    if isinstance(employment_type, str):
        employment_type = [employment_type]

    job_payload = {
        **generated_output,
        "companyId": COMPANY_ID,
        "locations": gen_payload["locations"],
        "employment_type": employment_type,
        "work_mode": gen_payload["work_mode"],
        "is_job_created": False,
    }

    token = get_token()
    job_response = create_job(job_payload, token)
    print("Create Job Status:", job_response.status_code)
    print("Create Job Response:", job_response.text)
    assert job_response.status_code == 201

    print("Job Created")

    created_job = job_response.json()["data"]["data"]
    job_prefix = created_job["job_prefix"]

    # STEP 3 - application form
    app_payload = {
        "companyId": job_payload["companyId"],
        "job_prefix": job_prefix,
        "is_visible_publically": True,
        "acceptingSubmissions": True,
        "autoReview": True,
        "questions": job_payload.get("questions", [])
    }

    app_response = save_application(job_prefix, app_payload)
    assert app_response.status_code == 201

    print("Application Form Created")

    # STEP 4 - run aggregator
    aggregator_response = run_job_aggregator(job_prefix, token)
    print("Aggregator Status:", aggregator_response.status_code)
    print("Aggregator Response:", aggregator_response.text)
    assert aggregator_response.status_code == 201

    print("Aggregator Completed")

    # STEP 5 - publish job
    publish_payload = {
        **created_job,
        "job_status": "active",
        "is_job_created": True,

    }

    publish_response = publish_job(job_prefix, publish_payload, token)
    print("Publish Status:", publish_response.status_code)
    print("Publish Response:", publish_response.text)
    assert publish_response.status_code == 200

    print("Job Published")

    # STEP 6 - verify aggregator GET response after publication
    # frontend calls: GET /company/backend/aggregator/{job_prefix}
    from config.config import BASE_URL
    from utils.api_client import APIClient

    api_client = APIClient()
    aggregator_get_response = api_client.get(
        f"{BASE_URL}/aggregator/{job_prefix}",
        headers={"Authorization": f"Bearer {token}"}
    )

    print("Aggregator GET Status:", aggregator_get_response.status_code)
    assert aggregator_get_response.status_code in (200, 304)

    if aggregator_get_response.status_code == 200:
        body = aggregator_get_response.json()
        assert body.get("status") == "success"
        data = body.get("data")
        assert data is not None
        assert "companyData" in data
        assert "job" in data
        assert data["job"].get("job_prefix") == job_prefix
        assert data["job"].get("job_status") == "published"


