import json
import os
import re

import requests
from dotenv import load_dotenv

from config.config import OPENROUTER_API_KEY, OPENROUTER_MODEL


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"


def _extract_json_array(text):
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            raise ValueError(f"OpenRouter did not return a JSON array: {text}")
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, list):
        raise ValueError("OpenRouter response must be a JSON array.")

    return parsed


def _extract_json_object(text):
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError(f"OpenRouter did not return a JSON object: {text}")
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("OpenRouter response must be a JSON object.")

    return parsed


def _get_openrouter_settings():
    load_dotenv()
    api_key = OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key == "paste_your_openrouter_api_key_here":
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Add it in config/config.py."
        )

    model = OPENROUTER_MODEL or os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
    return api_key, model


def _post_openrouter(messages, temperature=0.2):
    api_key, model = _get_openrouter_settings()
    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "API Testing Project",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
        },
        timeout=120,
    )

    return response, model


def generate_job_roles(job_family, count, experience_range, question_mode, duration):
    prompt = f"""
Generate {count} interview job role drafts for the job family: {job_family}.
Experience range must be exactly: {experience_range}.
Question mode must be exactly: {question_mode}.
Interview duration must be exactly: {duration}.

Return only a JSON array. Each item must use this exact schema:
{{
  "title": "Role Name",
  "role": "Role Name",
  "duration": {duration},
  "experience_level": "{experience_range}",
  "seniority": "Junior|Mid|Senior",
  "interviewCategory": "technical",
  "question_mode": "{question_mode}",
  "feedbackType": "ASK",
  "visibility": "PUBLIC",
  "org_type": "company"
}}

Use realistic role names. For engineering examples, use roles like Python Developer,
Java Developer, Frontend Developer, DevOps Engineer, QA Automation Engineer, etc.
Do not include duplicate role names.
"""

    messages = [
        {
            "role": "system",
            "content": "You generate strict JSON only. No markdown.",
        },
        {"role": "user", "content": prompt},
    ]
    response, model = _post_openrouter(messages, temperature=0.4)
    print(f"[OPENROUTER] Generating {count} roles using {model}...", flush=True)
    print(f"[OPENROUTER] Status: {response.status_code}", flush=True)
    if response.status_code != 200:
        raise RuntimeError(f"OpenRouter failed: {response.text}")

    content = response.json()["choices"][0]["message"]["content"]
    return _extract_json_array(content)


def verify_interview_plan(role_title, experience_range, duration, question_mode, interview_plan):
    prompt = f"""
Evaluate whether this interview plan is appropriate for the requested role.

Requested role: {role_title}
Experience range: {experience_range}
Duration minutes: {duration}
Question mode: {question_mode}

Interview plan JSON:
{json.dumps(interview_plan, ensure_ascii=True)}

Return only a JSON object with this exact schema:
{{
  "rating": 0,
  "verdict": "pass|needs_review|fail",
  "reason": "one concise sentence",
  "factor_scores": {{
    "role_relevance": {{"score": 0, "reason": "short reason"}},
    "experience_fit": {{"score": 0, "reason": "short reason"}},
    "skill_coverage": {{"score": 0, "reason": "short reason"}},
    "time_allocation": {{"score": 0, "reason": "short reason"}},
    "specificity": {{"score": 0, "reason": "short reason"}}
  }},
  "role_alignment_notes": ["short note 1", "short note 2"],
  "missing_or_weak_topics": ["topic if any"]
}}

Rate the final rating out of 10. Also rate each factor out of 10:
role relevance, seniority/experience fit, coverage of role-specific skills,
time allocation, and whether the plan avoids generic or unrelated topics.
"""

    messages = [
        {
            "role": "system",
            "content": "You are a strict interview design reviewer. Return strict JSON only.",
        },
        {"role": "user", "content": prompt},
    ]
    print(f"[OPENROUTER] Verifying interview plan for {role_title}...", flush=True)
    response, _model = _post_openrouter(messages, temperature=0.1)
    print(f"[OPENROUTER] Verification status: {response.status_code}", flush=True)
    if response.status_code != 200:
        raise RuntimeError(f"OpenRouter verification failed: {response.text}")

    content = response.json()["choices"][0]["message"]["content"]
    result = _extract_json_object(content)
    result["rating"] = max(0, min(10, float(result.get("rating", 0))))
    result["verdict"] = str(result.get("verdict", "needs_review"))
    result["reason"] = str(result.get("reason", "")).strip()
    result["factor_scores"] = result.get("factor_scores") or {}
    result["role_alignment_notes"] = result.get("role_alignment_notes") or []
    result["missing_or_weak_topics"] = result.get("missing_or_weak_topics") or []
    return result
