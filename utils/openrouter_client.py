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


def generate_job_roles(job_family, count, experience_range):
    load_dotenv()
    api_key = OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key == "paste_your_openrouter_api_key_here":
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Add it in config/config.py."
        )

    model = OPENROUTER_MODEL or os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
    prompt = f"""
Generate {count} interview job role drafts for the job family: {job_family}.
Experience range must be exactly: {experience_range}.

Return only a JSON array. Each item must use this exact schema:
{{
  "title": "Role Name",
  "role": "Role Name",
  "duration": 10,
  "experience_level": "{experience_range}",
  "seniority": "Junior|Mid|Senior",
  "interviewCategory": "technical",
  "question_mode": "DIRECT",
  "feedbackType": "ASK",
  "visibility": "PUBLIC",
  "org_type": "company"
}}

Use realistic role names. For engineering examples, use roles like Python Developer,
Java Developer, Frontend Developer, DevOps Engineer, QA Automation Engineer, etc.
Do not include duplicate role names.
"""

    print(f"[OPENROUTER] Generating {count} roles using {model}...", flush=True)
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
            "messages": [
                {
                    "role": "system",
                    "content": "You generate strict JSON only. No markdown.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        },
        timeout=120,
    )

    print(f"[OPENROUTER] Status: {response.status_code}", flush=True)
    if response.status_code != 200:
        raise RuntimeError(f"OpenRouter failed: {response.text}")

    content = response.json()["choices"][0]["message"]["content"]
    return _extract_json_array(content)
