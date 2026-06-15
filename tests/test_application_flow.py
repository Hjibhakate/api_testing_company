from services.auth_service import current_user, get_token
from services.application_service import save_application
from services.job_create import create_job, publish_job, run_job_aggregator


def test_job_creation_flow():
    # STEP 1 - get token
    token = get_token()
    assert token is not None

    # STEP 2 - generate job description (use AI JD, like job_flow)
    from services.job_service import generate_job_description

    # Roles + experience (set exactly as you requested)
    # Example you gave: "2 year Py developer", "4 year python developer", "6 year python developer".
    # Here we apply the same idea: each role gets its own experience.
    job_specs = [
        {"jobRole": "Python Developer", "experience": "2"},
        {"jobRole": "SDET", "experience": "4"},
        {"jobRole": "QA Engineer", "experience": "2"},
        {"jobRole": "Analytics Engineer", "experience": "5"},
        {"jobRole": "Java Developer", "experience": "6"},
        {"jobRole": "DevOps Engineer", "experience": "4"},
        {"jobRole": "Backend Developer", "experience": "5"},
        {"jobRole": "Frontend Developer", "experience": "2"},
        {"jobRole": "Power BI Developer", "experience": "6"},
        {"jobRole": "React Developer", "experience": "4"},
        {"jobRole": "AI Engineer", "experience": "5"},
        {"jobRole": "AI Researcher", "experience": "6"},
        {"jobRole": "Project Manager", "experience": "2"},
        {"jobRole": "Business Analyst", "experience": "4"},
    ]

    for spec in job_specs:
        gen_payload = {
            "modelName": "AI",
            "jobRole": spec["jobRole"],
            "experience": spec["experience"],
            "locations": ["Nagpur, India"],
            "employment_type": ["Full-time"],
            "work_mode": ["On-site"],
        }

        gen_response = generate_job_description(gen_payload)
        assert gen_response.status_code == 201

        print(f"Job Description Generated for {spec['jobRole']} ({spec['experience']} years)")

        generated_output = gen_response.json()["data"]["data"]["output"]
        employment_type = generated_output.get(
            "employment_type", gen_payload["employment_type"]
        )
        if isinstance(employment_type, str):
            employment_type = [employment_type]

        job_payload = {
            **generated_output,
            "companyId": "c2af53c8-073f-4d18-a0b2-ed5735abea45",
            "locations": gen_payload["locations"],
            "employment_type": employment_type,
            "work_mode": gen_payload["work_mode"],
            # Always create as active
            "job_status": "active",
            "is_job_created": False,
        }

        # STEP 3 - API call
        response = create_job(job_payload, token)
        print("Response:", response.text)
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
            "questions": job_payload.get("questions", []),
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
            # Always publish to active
            "job_status": "active",
            "is_job_created": True,
        }

        publish_response = publish_job(job_prefix, publish_payload, token)
        print("Publish Response:", publish_response.text)
        assert publish_response.status_code == 200

        published_job = publish_response.json()["data"]["data"]
        assert published_job["job_status"] == "active"
        assert published_job["is_job_created"] is True

    # STEP 8 - verify current user after all publish redirect
    current_user_response = current_user(token)
    print("Current User Response:", current_user_response.text)
    assert current_user_response.status_code in (200, 304)

    print("JOBS PUBLISHED SUCCESSFULLY")

