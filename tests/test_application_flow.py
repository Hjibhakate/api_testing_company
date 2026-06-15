from services.auth_service import current_user, get_token
from services.application_service import save_application
from services.job_create import create_job, publish_job, run_job_aggregator

def test_job_creation_flow():

    # STEP 1 - get token
    token = get_token()
    assert token is not None

    # STEP 2 - generate job description (use AI JD, like job_flow)
    from services.job_service import generate_job_description

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

    generated_output = gen_response.json()["data"]["data"]["output"]
    employment_type = generated_output.get("employment_type", gen_payload["employment_type"])
    if isinstance(employment_type, str):
        employment_type = [employment_type]

    job_payload = {
        **generated_output,
        "companyId": "c2af53c8-073f-4d18-a0b2-ed5735abea45",
        "locations": gen_payload["locations"],
        "employment_type": employment_type,
        "work_mode": gen_payload["work_mode"],
        "job_status": "draft",
        "is_job_created": False,
    }



    # STEP 3 - API call
    response = create_job(job_payload, token)

    print("Response:", response.text)

    # STEP 4 - validation
    assert response.status_code == 201

    job_data = response.json()
    assert "data" in job_data

    created_job = job_data["data"]["data"]
    job_prefix = created_job["job_prefix"]

    # STEP 5 - create application form
    app_payload = {
        "companyId": job_payload["companyId"],
        "job_prefix": job_prefix,
        "is_visible_publically": True,
        "acceptingSubmissions": True,
        "autoReview": True,
        "questions": job_payload.get("questions", [])
    }

    app_response = save_application(job_prefix, app_payload)
    print("Application Response:", app_response.text)
    assert app_response.status_code == 201

    # STEP 6 - run aggregator
    aggregator_response = run_job_aggregator(job_prefix, token)
    print("Aggregator Response:", aggregator_response.text)
    assert aggregator_response.status_code == 201

    # STEP 7 - publish job
    publish_payload = {
        **created_job,
        "job_status": "published",
        "is_job_created": True,
    }

    publish_response = publish_job(job_prefix, publish_payload, token)
    print("Publish Response:", publish_response.text)
    assert publish_response.status_code == 200

    published_job = publish_response.json()["data"]["data"]
    assert published_job["job_status"] == "published"
    assert published_job["is_job_created"] is True

    # STEP 8 - verify current user after publish redirect
    current_user_response = current_user(token)
    print("Current User Response:", current_user_response.text)
    assert current_user_response.status_code in (200, 304)

    print("JOB PUBLISHED SUCCESSFULLY")
