from __future__ import annotations

import argparse
import contextlib
import json
import os
import queue
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from generate_interview_sets import build_draft, create_one_interview_set
from utils.auth_helper import get_token
from utils.openrouter_client import generate_job_roles


ROOT = Path(__file__).resolve().parent
LOGS: list[dict[str, Any]] = []
LOG_QUEUE: queue.Queue[dict[str, Any]] = queue.Queue()
RATINGS: list[dict[str, Any]] = []
RATINGS_LOCK = threading.Lock()
PROCESS: subprocess.Popen[str] | None = None
PROCESS_LOCK = threading.Lock()
CANCEL_EVENT = threading.Event()
RUNNING = False
EXIT_CODE: int | None = None


class LogWriter:
    def __init__(self, kind: str = "") -> None:
        self.kind = kind
        self._buffer = ""

    def write(self, text: str) -> int:
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                add_log(line, classify_line(line))
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            add_log(self._buffer, self.kind)
            self._buffer = ""


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Interview Set Studio</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #eef2f5;
      --panel: #ffffff;
      --panel-soft: #f9fbfd;
      --ink: #17212f;
      --muted: #687586;
      --line: #d8e0e8;
      --line-strong: #bfccd8;
      --accent: #14675f;
      --accent-dark: #0f514b;
      --accent-soft: #e8f4f2;
      --danger: #b42318;
      --danger-soft: #fff0ee;
      --ok: #277a45;
      --ok-soft: #edf8f1;
      --warn: #b7791f;
      --terminal: #121821;
      --terminal-top: #1b2430;
      --terminal-ink: #dfeaf6;
      --shadow: 0 18px 48px rgba(23, 33, 47, 0.1);
      --shadow-soft: 0 4px 16px rgba(23, 33, 47, 0.07);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(180deg, #f8fafc 0, var(--bg) 310px);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    main {
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 26px 0 30px;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 20px;
    }

    h1 {
      margin: 0;
      font-size: 25px;
      line-height: 1.2;
      letter-spacing: 0;
    }

    .subtitle {
      margin-top: 5px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
    }

    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 38px;
      padding: 7px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--muted);
      font-size: 14px;
      font-weight: 650;
      white-space: nowrap;
      box-shadow: var(--shadow-soft);
    }

    .dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: var(--muted);
    }

    .dot.running { background: var(--warn); }
    .dot.pass { background: var(--ok); }
    .dot.fail { background: var(--danger); }

    .workspace {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 300px;
      gap: 18px;
      align-items: start;
      margin-bottom: 18px;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      box-shadow: var(--shadow-soft);
      overflow: hidden;
    }

    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 16px 18px 13px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #ffffff, #fbfcfe);
    }

    h2 {
      margin: 0;
      font-size: 16px;
      line-height: 1.25;
      letter-spacing: 0;
    }

    .eyebrow {
      margin: 0 0 6px;
      color: var(--accent);
      font-size: 11px;
      font-weight: 760;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .panel-copy {
      margin: 3px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }

    .generator-form {
      display: grid;
      grid-template-columns: minmax(180px, 1fr) 92px minmax(150px, 180px);
      gap: 14px;
      padding: 18px;
    }

    .options-grid {
      grid-column: 1 / -1;
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 14px;
    }

    .form-actions {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 10px;
      padding-top: 4px;
    }

    .test-panel {
      min-height: 100%;
      display: flex;
      flex-direction: column;
    }

    .test-actions {
      display: grid;
      gap: 11px;
      padding: 18px;
    }

    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      line-height: 1.25;
    }

    input, select {
      width: 100%;
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0 11px;
      color: var(--ink);
      background: #fff;
      font: inherit;
      font-size: 14px;
      font-weight: 520;
      outline: none;
      transition: border-color 120ms ease, box-shadow 120ms ease;
    }

    input:focus, select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-soft);
    }

    .controls {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    button {
      min-height: 42px;
      border: 0;
      border-radius: 8px;
      padding: 0 17px;
      color: #fff;
      background: var(--accent);
      font: inherit;
      font-weight: 650;
      cursor: pointer;
      box-shadow: 0 1px 2px rgba(24, 39, 75, 0.08);
      transition: background 120ms ease, transform 120ms ease, box-shadow 120ms ease;
    }

    button:hover {
      background: var(--accent-dark);
      box-shadow: 0 5px 14px rgba(18, 107, 99, 0.2);
    }

    button:active { transform: translateY(1px); }

    button:disabled {
      cursor: not-allowed;
      background: #8a97a8;
      box-shadow: none;
    }

    .ghost {
      background: #edf2f7;
      color: var(--ink);
      border: 1px solid var(--line);
    }

    .ghost:hover { background: #dce4ef; }

    .danger-button {
      background: var(--danger);
    }

    .danger-button:hover {
      background: #8f1d14;
      box-shadow: 0 5px 14px rgba(180, 35, 24, 0.18);
    }

    .wide-button {
      width: 100%;
    }

    .summary-list {
      display: grid;
      gap: 9px;
      margin-top: 2px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-soft);
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }

    .summary-row {
      display: flex;
      justify-content: space-between;
      gap: 10px;
    }

    .summary-row strong {
      color: var(--ink);
      font-weight: 720;
      white-space: nowrap;
    }

    .ratings-panel {
      margin-bottom: 18px;
    }

    .ratings-list {
      display: grid;
      gap: 10px;
      padding: 14px 18px 18px;
    }

    .criteria-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 10px;
      padding: 14px 18px 0;
    }

    .criteria-item {
      min-height: 70px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-soft);
    }

    .criteria-item strong {
      display: block;
      margin-bottom: 5px;
      color: var(--ink);
      font-size: 12px;
      line-height: 1.25;
    }

    .criteria-item span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }

    .ratings-empty {
      color: var(--muted);
      font-size: 13px;
      padding: 4px 0;
    }

    .rating-card {
      display: grid;
      grid-template-columns: 96px minmax(0, 1fr);
      gap: 12px;
      align-items: start;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-soft);
    }

    .score {
      display: grid;
      place-items: center;
      min-height: 72px;
      border-radius: 8px;
      background: #ffffff;
      border: 1px solid var(--line);
    }

    .score strong {
      color: var(--accent);
      font-size: 25px;
      line-height: 1;
    }

    .score span {
      color: var(--muted);
      font-size: 12px;
      margin-top: 3px;
    }

    .rating-body h3 {
      margin: 0 0 5px;
      font-size: 14px;
      line-height: 1.25;
    }

    .verdict {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 0 8px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 750;
      text-transform: capitalize;
    }

    .rating-reason {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }

    .weak-topics {
      margin-top: 8px;
      color: var(--danger);
      font-size: 12px;
      line-height: 1.4;
    }

    .factor-breakdown {
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 8px;
      margin-top: 12px;
    }

    .factor-score {
      padding: 9px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }

    .factor-score strong {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      color: var(--ink);
      font-size: 12px;
      line-height: 1.25;
    }

    .factor-score b {
      color: var(--accent);
      font-size: 13px;
      white-space: nowrap;
    }

    .factor-score span {
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }

    .log-shell {
      border: 1px solid #263448;
      border-radius: 10px;
      overflow: hidden;
      background: var(--terminal);
      box-shadow: var(--shadow);
    }

    .log-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-height: 44px;
      padding: 0 12px 0 14px;
      background: var(--terminal-top);
      color: #a8b7c8;
      border-bottom: 1px solid #2b394b;
      font-size: 13px;
    }

    .log-title {
      font-weight: 700;
      color: #e9f1fb;
    }

    .hint {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.4;
    }

    .terminal {
      height: min(68vh, 720px);
      min-height: 420px;
      overflow: auto;
      background: var(--terminal);
      color: var(--terminal-ink);
      padding: 15px;
      font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
      font-size: 13px;
      line-height: 1.58;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .terminal:empty::before {
      content: "Ready.";
      color: #7f90a5;
    }

    .kbd {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 0 7px;
      border-radius: 6px;
      background: #263448;
      color: #dfeaf6;
      font-size: 12px;
      font-weight: 700;
    }

    .line.meta { color: #8fb3d9; }
    .line.pass { color: #9be29d; }
    .line.fail { color: #ff9b9b; }

    @media (max-width: 980px) {
      .workspace { grid-template-columns: 1fr; }
      .generator-form { grid-template-columns: minmax(0, 1fr) 110px; }
      .generator-form label:nth-child(3) { grid-column: 1 / -1; }
      .options-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .criteria-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .factor-breakdown { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }

    @media (max-width: 680px) {
      main { width: min(100vw - 20px, 1120px); padding-top: 14px; }
      .topbar, .panel-head, .form-actions { align-items: stretch; flex-direction: column; }
      .generator-form, .options-grid { grid-template-columns: 1fr; }
      .criteria-grid { grid-template-columns: 1fr; }
      .factor-breakdown { grid-template-columns: 1fr; }
      .rating-card { grid-template-columns: 1fr; }
      .generator-form label:nth-child(3) { grid-column: auto; }
      .status { width: 100%; }
      .terminal { min-height: 56vh; height: 62vh; }
    }
  </style>
</head>
<body>
  <main>
    <div class="topbar">
      <div>
        <h1>Interview Set Studio</h1>
        <div class="subtitle">Create interview sets with controlled inputs, verified API execution, and live run logs.</div>
      </div>
      <div class="status"><span id="dot" class="dot"></span><span id="statusText">Ready</span></div>
    </div>

    <div class="workspace">
      <section class="panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Generator</p>
            <h2>Create Interview Sets</h2>
            <p class="panel-copy">Choose the role family and interview settings before creating sets.</p>
          </div>
        </div>

        <div class="generator-form">
          <label>
            Job type
            <input id="jobFamily" type="text" value="Engineering">
          </label>
          <label>
            Roles
            <input id="roleCount" type="number" min="1" max="50" value="5">
          </label>
          <label>
            Experience
            <input id="experienceRange" type="text" value="1-2 years">
          </label>

          <div class="options-grid">
            <label>
              Mode
              <select id="questionMode">
                <option value="DIRECT">Direct</option>
                <option value="SCENARIO">Scenario</option>
                <option value="BEI">BEI</option>
              </select>
            </label>
            <label>
              Minutes
              <input id="duration" type="number" min="1" value="30">
            </label>
            <label>
              AI voice
              <select id="aiVoiceGender">
                <option value="FEMALE">Female</option>
                <option value="MALE">Male</option>
              </select>
            </label>
            <label>
              AI avatar
              <select id="aiAvatarGender">
                <option value="FEMALE">Female</option>
                <option value="MALE">Male</option>
              </select>
            </label>
          </div>

          <div class="form-actions">
            <button id="generateBtn" type="button">Generate Interview Sets</button>
          </div>
        </div>
      </section>

      <section class="panel test-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Checks</p>
            <h2>Verification</h2>
            <p class="panel-copy">Run tests and clear the output when needed.</p>
          </div>
        </div>
        <div class="test-actions">
          <button id="runBtn" class="wide-button" type="button">Run Tests</button>
          <button id="cancelBtn" class="danger-button wide-button" type="button" disabled>Cancel Run</button>
          <button id="clearBtn" class="ghost wide-button" type="button">Clear Log</button>
          <div class="summary-list">
            <div class="summary-row"><span>Execution</span><strong>Live</strong></div>
            <div class="summary-row"><span>Runner</span><strong>pytest</strong></div>
            <div class="summary-row"><span>Output</span><strong>Streamed</strong></div>
          </div>
        </div>
      </section>
    </div>

    <section class="panel ratings-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Quality</p>
          <h2>Plan Ratings</h2>
          <p class="panel-copy">OpenRouter review scores for each generated interview plan.</p>
        </div>
      </div>
      <div class="criteria-grid">
        <div class="criteria-item">
          <strong>Role Relevance</strong>
          <span>How closely topics match the selected job role.</span>
        </div>
        <div class="criteria-item">
          <strong>Experience Fit</strong>
          <span>Whether depth matches the selected experience range.</span>
        </div>
        <div class="criteria-item">
          <strong>Skill Coverage</strong>
          <span>Coverage of core skills expected for the role.</span>
        </div>
        <div class="criteria-item">
          <strong>Time Allocation</strong>
          <span>Whether phases fit the interview duration.</span>
        </div>
        <div class="criteria-item">
          <strong>Specificity</strong>
          <span>Checks that topics are not generic or unrelated.</span>
        </div>
      </div>
      <div id="ratingsList" class="ratings-list">
        <div class="ratings-empty">Ratings will appear after each plan is reviewed.</div>
      </div>
    </section>

    <div class="log-shell">
      <div class="log-head">
        <span class="log-title">Live Activity</span>
        <span class="hint"><span class="kbd">log</span> Streaming output</span>
      </div>
      <div id="terminal" class="terminal" aria-live="polite"></div>
    </div>
  </main>

  <script>
    const runBtn = document.getElementById("runBtn");
    const generateBtn = document.getElementById("generateBtn");
    const cancelBtn = document.getElementById("cancelBtn");
    const clearBtn = document.getElementById("clearBtn");
    const jobFamily = document.getElementById("jobFamily");
    const roleCount = document.getElementById("roleCount");
    const experienceRange = document.getElementById("experienceRange");
    const questionMode = document.getElementById("questionMode");
    const duration = document.getElementById("duration");
    const aiVoiceGender = document.getElementById("aiVoiceGender");
    const aiAvatarGender = document.getElementById("aiAvatarGender");
    const terminal = document.getElementById("terminal");
    const ratingsList = document.getElementById("ratingsList");
    const statusText = document.getElementById("statusText");
    const dot = document.getElementById("dot");
    let nextIndex = 0;
    let pollTimer = null;

    function appendLine(entry) {
      const div = document.createElement("div");
      div.className = `line ${entry.kind || ""}`;
      div.textContent = entry.text;
      terminal.appendChild(div);
      terminal.scrollTop = terminal.scrollHeight;
    }

    function setStatus(state) {
      dot.className = "dot";
      if (state.running) {
        dot.classList.add("running");
        statusText.textContent = "Running";
        runBtn.disabled = true;
        generateBtn.disabled = true;
        cancelBtn.disabled = false;
        return;
      }

      runBtn.disabled = false;
      generateBtn.disabled = false;
      cancelBtn.disabled = true;
      if (state.exit_code === 0) {
        dot.classList.add("pass");
        statusText.textContent = "Passed";
      } else if (state.exit_code === null || state.exit_code === undefined) {
        statusText.textContent = "Ready";
      } else {
        dot.classList.add("fail");
        statusText.textContent = `Failed (${state.exit_code})`;
      }
    }

    async function pollLogs() {
      const response = await fetch(`/logs?after=${nextIndex}`);
      const data = await response.json();
      data.logs.forEach(appendLine);
      nextIndex = data.next;
      setStatus(data);
      await pollRatings();
      if (!data.running && pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    }

    function renderRatings(ratings) {
      if (!ratings.length) {
        ratingsList.innerHTML = '<div class="ratings-empty">Ratings will appear after each plan is reviewed.</div>';
        return;
      }

      const factorLabels = {
        role_relevance: "Role Relevance",
        experience_fit: "Experience Fit",
        skill_coverage: "Skill Coverage",
        time_allocation: "Time Allocation",
        specificity: "Specificity"
      };

      ratingsList.innerHTML = ratings.map((item) => {
        const weakTopics = item.weak_topics && item.weak_topics.length
          ? `<div class="weak-topics">Weak topics: ${item.weak_topics.join(", ")}</div>`
          : "";
        const factorScores = item.factor_scores || {};
        const factorKeys = Object.keys(factorLabels);
        const factorBreakdown = factorKeys.some((key) => factorScores[key])
          ? `
            <div class="factor-breakdown">
              ${factorKeys.map((key) => {
                const factor = factorScores[key] || {};
                const score = factor.score ?? "-";
                const reason = factor.reason || "No detail returned.";
                return `
                  <div class="factor-score">
                    <strong>${factorLabels[key]} <b>${score}/10</b></strong>
                    <span>${reason}</span>
                  </div>
                `;
              }).join("")}
            </div>
          `
          : '<p class="rating-reason">Detailed factor breakdown will appear for new ratings.</p>';
        return `
          <div class="rating-card">
            <div class="score"><strong>${item.rating}</strong><span>/ 10</span></div>
            <div class="rating-body">
              <h3>${item.role}</h3>
              <span class="verdict">${String(item.verdict || "needs_review").replace("_", " ")}</span>
              <p class="rating-reason">${item.reason || "No reason returned."}</p>
              ${factorBreakdown}
              ${weakTopics}
            </div>
          </div>
        `;
      }).join("");
    }

    async function pollRatings() {
      const response = await fetch("/ratings");
      const data = await response.json();
      renderRatings(data.ratings || []);
    }

    async function startRun() {
      const response = await fetch("/run", { method: "POST" });
      const data = await response.json();
      if (!data.ok) {
        appendLine({ kind: "fail", text: data.message });
        setStatus(data);
        return;
      }
      nextIndex = 0;
      terminal.textContent = "";
      setStatus(data);
      if (!pollTimer) {
        pollTimer = setInterval(pollLogs, 700);
      }
      pollLogs();
    }

    async function startGenerate() {
      const payload = {
        job_family: jobFamily.value.trim() || "Engineering",
        count: Number(roleCount.value || 1),
        experience_range: experienceRange.value.trim() || "1-2 years",
        question_mode: questionMode.value || "DIRECT",
        duration: Number(duration.value || 30),
        ai_voice_gender: aiVoiceGender.value || "FEMALE",
        ai_avatar_gender: aiAvatarGender.value || "FEMALE"
      };

      const response = await fetch("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!data.ok) {
        appendLine({ kind: "fail", text: data.message });
        setStatus(data);
        return;
      }
      nextIndex = 0;
      terminal.textContent = "";
      setStatus(data);
      if (!pollTimer) {
        pollTimer = setInterval(pollLogs, 700);
      }
      pollLogs();
    }

    async function cancelRun() {
      const response = await fetch("/cancel", { method: "POST" });
      const data = await response.json();
      appendLine({ kind: data.ok ? "fail" : "meta", text: data.message });
      setStatus(data);
    }

    runBtn.addEventListener("click", startRun);
    generateBtn.addEventListener("click", startGenerate);
    cancelBtn.addEventListener("click", cancelRun);
    clearBtn.addEventListener("click", () => {
      terminal.textContent = "";
      nextIndex = 0;
      renderRatings([]);
    });

    pollLogs();
    pollRatings();
  </script>
</body>
</html>
"""


def add_log(text: str, kind: str = "") -> None:
    entry = {"text": text.rstrip("\n"), "kind": kind}
    LOG_QUEUE.put(entry)


def add_rating(draft: dict[str, Any], review: dict[str, Any]) -> None:
    with RATINGS_LOCK:
        RATINGS.append(
            {
                "role": draft.get("title") or draft.get("role") or "Untitled role",
                "rating": review.get("rating", 0),
                "verdict": review.get("verdict", "needs_review"),
                "reason": review.get("reason", ""),
                "factor_scores": review.get("factor_scores") or {},
                "weak_topics": review.get("missing_or_weak_topics") or [],
            }
        )


def drain_logs() -> None:
    while True:
        try:
            LOGS.append(LOG_QUEUE.get_nowait())
        except queue.Empty:
            return


def classify_line(line: str) -> str:
    lowered = line.lower()
    if " failed" in lowered or "error" in lowered or "traceback" in lowered:
        return "fail"
    if " passed" in lowered or "login flow passed" in lowered:
        return "pass"
    if line.startswith("["):
        return "meta"
    return ""


def run_pytest() -> None:
    global EXIT_CODE, PROCESS, RUNNING

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    command = [sys.executable, "-u", "-m", "pytest"]
    add_log(f"$ {' '.join(command)}", "meta")

    try:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        with PROCESS_LOCK:
            PROCESS = process

        assert process.stdout is not None
        for line in process.stdout:
            add_log(line, classify_line(line))

        code = process.wait()
        EXIT_CODE = code
        kind = "pass" if code == 0 else "fail"
        add_log(f"Process finished with exit code {code}", kind)
    except Exception as exc:
        EXIT_CODE = 1
        add_log(f"Could not run pytest: {exc}", "fail")
    finally:
        with PROCESS_LOCK:
            PROCESS = None
            RUNNING = False
            CANCEL_EVENT.clear()


def run_interview_set_generator(
    job_family: str,
    count: int,
    experience_range: str,
    question_mode: str,
    duration: int,
    ai_voice_gender: str,
    ai_avatar_gender: str,
) -> None:
    global EXIT_CODE, RUNNING

    try:
        add_log("[UI] Starting AI interview set generator.", "meta")
        add_log(f"[UI] Job type: {job_family}", "meta")
        add_log(f"[UI] Role count: {count}", "meta")
        add_log(f"[UI] Experience range: {experience_range}", "meta")
        add_log(f"[UI] Question mode: {question_mode}", "meta")
        add_log(f"[UI] Duration: {duration} minutes", "meta")
        add_log(f"[UI] AI voice: {ai_voice_gender}", "meta")
        add_log(f"[UI] AI avatar: {ai_avatar_gender}", "meta")

        writer = LogWriter()
        with contextlib.redirect_stdout(writer):
            roles = generate_job_roles(
                job_family,
                count,
                experience_range,
                question_mode,
                duration,
            )
            print("[UI] Generated roles:", flush=True)
            for index, role in enumerate(roles, start=1):
                print(f"{index}. {role['title']} ({role.get('seniority', 'Senior')})", flush=True)

            token = get_token()
            success_count = 0

            for role in roles:
                if CANCEL_EVENT.is_set():
                    print("[UI] Cancel requested. Stopping before next role.", flush=True)
                    break

                draft = build_draft(
                    role,
                    experience_range,
                    question_mode,
                    duration,
                    ai_voice_gender,
                    ai_avatar_gender,
                )
                print(f"\n[CREATE] Starting: {draft['title']}", flush=True)
                if create_one_interview_set(
                    token,
                    draft,
                    should_cancel=CANCEL_EVENT.is_set,
                    review_callback=add_rating,
                ):
                    success_count += 1

            print(
                f"\nFinished. Created {success_count}/{len(roles)} interview sets.",
                flush=True,
            )
        writer.flush()
        EXIT_CODE = 0
        add_log("[UI] Generator finished.", "pass")
    except Exception as exc:
        EXIT_CODE = 1
        add_log(f"[UI] Generator failed: {exc}", "fail")
    finally:
        RUNNING = False
        CANCEL_EVENT.clear()


def clear_logs() -> None:
    LOGS.clear()
    with RATINGS_LOCK:
        RATINGS.clear()
    while not LOG_QUEUE.empty():
        try:
            LOG_QUEUE.get_nowait()
        except queue.Empty:
            break


def start_pytest() -> tuple[bool, str]:
    global EXIT_CODE, RUNNING

    with PROCESS_LOCK:
        if RUNNING:
            return False, "Another process is already running."

        CANCEL_EVENT.clear()
        RUNNING = True
        EXIT_CODE = None
        clear_logs()

    thread = threading.Thread(target=run_pytest, daemon=True)
    thread.start()
    return True, "Started."


def start_generator(payload: dict[str, Any]) -> tuple[bool, str]:
    global EXIT_CODE, RUNNING

    job_family = str(payload.get("job_family") or "Engineering").strip()
    experience_range = str(payload.get("experience_range") or "1-2 years").strip()
    question_mode = str(payload.get("question_mode") or "DIRECT").strip().upper()
    ai_voice_gender = str(payload.get("ai_voice_gender") or "FEMALE").strip().upper()
    ai_avatar_gender = str(payload.get("ai_avatar_gender") or "FEMALE").strip().upper()
    try:
        count = int(payload.get("count") or 1)
    except (TypeError, ValueError):
        return False, "Role count must be a number."
    try:
        duration = int(payload.get("duration") or 30)
    except (TypeError, ValueError):
        return False, "Duration must be a number."

    if count < 1:
        return False, "Role count must be at least 1."
    if duration < 1:
        return False, "Duration must be at least 1 minute."
    if question_mode not in ("DIRECT", "SCENARIO", "BEI"):
        return False, "Question mode must be DIRECT, SCENARIO, or BEI."
    if ai_voice_gender not in ("MALE", "FEMALE"):
        return False, "AI voice must be MALE or FEMALE."
    if ai_avatar_gender not in ("MALE", "FEMALE"):
        return False, "AI avatar must be MALE or FEMALE."

    with PROCESS_LOCK:
        if RUNNING:
            return False, "Another process is already running."

        CANCEL_EVENT.clear()
        RUNNING = True
        EXIT_CODE = None
        clear_logs()

    thread = threading.Thread(
        target=run_interview_set_generator,
        args=(
            job_family,
            count,
            experience_range,
            question_mode,
            duration,
            ai_voice_gender,
            ai_avatar_gender,
        ),
        daemon=True,
    )
    thread.start()
    return True, "Started."


def cancel_current_run() -> tuple[bool, str]:
    global EXIT_CODE, RUNNING

    with PROCESS_LOCK:
        if not RUNNING:
            return False, "No process is running."

        CANCEL_EVENT.set()
        if PROCESS is not None and PROCESS.poll() is None:
            PROCESS.terminate()
            EXIT_CODE = 1
            RUNNING = False
            return True, "Test run cancelled."

    add_log("[UI] Cancel requested. Waiting for current API request to finish.", "fail")
    return True, "Cancel requested."


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_html(HTML)
            return

        if parsed.path == "/logs":
            query = parse_qs(parsed.query)
            after = int(query.get("after", ["0"])[0])
            drain_logs()
            payload = {
                "logs": LOGS[after:],
                "next": len(LOGS),
                "running": RUNNING,
                "exit_code": EXIT_CODE,
            }
            self.send_json(payload)
            return

        if parsed.path == "/ratings":
            with RATINGS_LOCK:
                ratings = list(RATINGS)
            self.send_json({"ratings": ratings})
            return

        self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/run":
            ok, message = start_pytest()
            self.send_json(
                {
                    "ok": ok,
                    "message": message,
                    "running": RUNNING,
                    "exit_code": EXIT_CODE,
                }
            )
            return

        if self.path == "/generate":
            payload = self.read_json_body()
            ok, message = start_generator(payload)
            self.send_json(
                {
                    "ok": ok,
                    "message": message,
                    "running": RUNNING,
                    "exit_code": EXIT_CODE,
                }
            )
            return

        if self.path == "/cancel":
            ok, message = cancel_current_run()
            self.send_json(
                {
                    "ok": ok,
                    "message": message,
                    "running": RUNNING,
                    "exit_code": EXIT_CODE,
                }
            )
            return

        else:
            self.send_error(404)
            return

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}

        raw_body = self.rfile.read(length)
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def send_json(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local browser UI for pytest runs.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"Test runner UI is available at {url}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
