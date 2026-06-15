from services.auth_service import get_token
from services.job_create import create_job

def test_job_creation_flow():

    # STEP 1 - get token
    token = get_token()
    assert token is not None

    # STEP 2 - create job payload (static test data)
    job_payload = {
        "jobRole": "QA Engineer",
        "experience_level": "2",
        "locations": ["Nagpur, India"],
        "employment_type": ["Full-time"],
        "work_mode": ["On-site"],
        "companyId": "c2af53c8-073f-4d18-a0b2-ed5735abea45",
        "job_status": "draft",
        "is_job_created": False
    }

    # STEP 3 - API call
    response = create_job(job_payload, token)

    print("Response:", response.text)

    # STEP 4 - validation
    assert response.status_code == 201

    job_data = response.json()
    assert "data" in job_data

    print("JOB CREATED SUCCESSFULLY")