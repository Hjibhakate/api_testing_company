# API Testing Project

This project automates interview set creation for the ACE interview platform.

It can:

- Log in using OTP.
- Generate job roles using OpenRouter AI.
- Create interview plans from the backend API.
- Verify each generated interview plan with OpenRouter.
- Show plan ratings out of 10.
- Save interview sets through the backend API.
- Run everything from either a browser UI or terminal.

## Run The UI

From the project root, run:

```powershell
python -B test_runner_ui.py
```

Then open:

```text
http://127.0.0.1:8765
```

The UI lets you select:

- Job type
- Number of roles
- Experience range
- Question mode: Direct, Scenario, or BEI
- Interview duration
- AI voice: Female or Male
- AI avatar: Female or Male

The UI also shows:

- Live logs
- Role-wise plan ratings
- Cancel button to stop a running process
- Test runner button

## Run From Terminal

From the project root, run:

```powershell
python generate_interview_sets.py
```

The script will ask for:

- Job role category
- Number of roles
- Experience range
- Question mode
- Interview duration
- AI voice
- AI avatar
- Final confirmation before creating interview sets
- Whether to invite a candidate after each interview set is created
- Candidate email address when invite is selected

## Run Tests

```powershell
python -m pytest
```

To run only the interview set flow:

```powershell
python -m pytest tests/test_interview_set_flow.py
```

## Configuration

Main configuration is in:

```text
config/config.py
```

Important values:

- `BASE_URL`
- `EMAIL`
- `EMAIL_PASSWORD`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`

Test data and default interview set values are in:

```text
test_data/test_data.py
```

This includes:

- Company ID
- Default draft payload
- AI voice IDs
- AI avatar URLs

## Main Files

```text
test_runner_ui.py
```

Local browser UI for generating interview sets, running tests, viewing logs, cancelling runs, and seeing plan ratings.

```text
generate_interview_sets.py
```

Terminal workflow for generating and creating interview sets.

```text
utils/openrouter_client.py
```

OpenRouter integration for generating roles and verifying interview plans.

```text
services/interview_set_service.py
```

Backend API calls for creating interview plans and saving interview sets.

```text
utils/auth_helper.py
```

OTP login helper that retrieves the auth token.

```text
utils/email_reader.py
```

Reads OTP emails from Gmail inbox.

```text
utils/api_client.py
```

Shared HTTP client with terminal logging.

```text
services/invite_service.py
```

Backend API calls for fetching candidates, inviting candidates, and sending Outlook invites.

## Flow

1. User selects role generation settings.
2. OpenRouter generates job roles.
3. The project logs in and gets a token.
4. For each role, the backend creates an interview plan.
5. OpenRouter verifies whether the plan matches the role.
6. The rating and reason are shown in the terminal and UI.
7. The interview set is saved using the verified plan.
8. In terminal mode, the script can ask whether to invite a candidate for that created set.
9. If selected, it fetches candidates, sends the interview-set invite, and sends the Outlook invite.

## Candidate Invite Flow

After each interview set is created in terminal mode, the script asks:

```text
Do you want to invite a candidate for <role> (<set-code>)? YES or NO
```

If you enter `YES`, it asks for the candidate email and calls:

```text
GET /interview-sets/{companyId}/{interviewSetCode}/candidates
POST /interview-sets/{companyId}/{interviewSetCode}/invite-candidates
POST /integrations/outlook/invite
```

The invite payload may need adjustment if the backend expects a different request body.

## Cancel Behavior

The UI has a `Cancel Run` button.

- Pytest runs stop immediately.
- Interview set generation stops safely after the current API/OpenRouter request finishes.
- If cancellation happens after verification and before save, the save step is skipped.
