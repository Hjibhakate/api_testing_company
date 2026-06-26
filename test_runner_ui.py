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
PROCESS: subprocess.Popen[str] | None = None
PROCESS_LOCK = threading.Lock()
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
  <title>API Test Runner</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --ink: #162033;
      --muted: #647084;
      --line: #d7dde8;
      --accent: #0b7a75;
      --accent-dark: #075f5b;
      --danger: #bd2f2f;
      --ok: #2f7d32;
      --terminal: #101723;
      --terminal-ink: #dce8f7;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    main {
      width: min(1120px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 24px 0;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 16px;
    }

    h1 {
      margin: 0;
      font-size: 24px;
      line-height: 1.2;
      letter-spacing: 0;
    }

    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 34px;
      padding: 6px 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--muted);
      font-size: 14px;
      white-space: nowrap;
    }

    .dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: var(--muted);
    }

    .dot.running { background: #d8941f; }
    .dot.pass { background: var(--ok); }
    .dot.fail { background: var(--danger); }

    .toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      margin-bottom: 16px;
    }

    .generator {
      display: grid;
      grid-template-columns: minmax(180px, 1fr) 100px minmax(150px, 1fr) 140px 120px auto;
      align-items: end;
      gap: 12px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      margin-bottom: 16px;
    }

    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.25;
    }

    input, select {
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0 10px;
      color: var(--ink);
      background: #fff;
      font: inherit;
    }

    .controls {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    button {
      min-height: 38px;
      border: 0;
      border-radius: 8px;
      padding: 0 14px;
      color: #fff;
      background: var(--accent);
      font: inherit;
      font-weight: 650;
      cursor: pointer;
    }

    button:hover { background: var(--accent-dark); }
    button:disabled {
      cursor: not-allowed;
      background: #8a97a8;
    }

    .ghost {
      background: #e7edf5;
      color: var(--ink);
    }

    .ghost:hover { background: #dce4ef; }

    .hint {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.4;
    }

    .terminal {
      height: min(68vh, 720px);
      min-height: 420px;
      overflow: auto;
      border-radius: 8px;
      background: var(--terminal);
      color: var(--terminal-ink);
      border: 1px solid #263448;
      padding: 14px;
      font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
      font-size: 13px;
      line-height: 1.55;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .line.meta { color: #8fb3d9; }
    .line.pass { color: #9be29d; }
    .line.fail { color: #ff9b9b; }

    @media (max-width: 680px) {
      main { width: min(100vw - 20px, 1120px); padding-top: 14px; }
      .topbar, .toolbar { align-items: stretch; flex-direction: column; }
      .generator { grid-template-columns: 1fr; }
      .status { width: 100%; }
      .terminal { min-height: 56vh; height: 62vh; }
    }
  </style>
</head>
<body>
  <main>
    <div class="topbar">
      <h1>API Test Runner</h1>
      <div class="status"><span id="dot" class="dot"></span><span id="statusText">Ready</span></div>
    </div>

    <div class="toolbar">
      <div class="controls">
        <button id="runBtn" type="button">Run Tests</button>
        <button id="clearBtn" class="ghost" type="button">Clear</button>
      </div>
      <div class="hint">Runs <strong>python -m pytest</strong> and shows live output here.</div>
    </div>

    <div class="generator">
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
      <button id="generateBtn" type="button">Generate Interview Sets</button>
    </div>

    <div id="terminal" class="terminal" aria-live="polite"></div>
  </main>

  <script>
    const runBtn = document.getElementById("runBtn");
    const generateBtn = document.getElementById("generateBtn");
    const clearBtn = document.getElementById("clearBtn");
    const jobFamily = document.getElementById("jobFamily");
    const roleCount = document.getElementById("roleCount");
    const experienceRange = document.getElementById("experienceRange");
    const questionMode = document.getElementById("questionMode");
    const duration = document.getElementById("duration");
    const terminal = document.getElementById("terminal");
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
        return;
      }

      runBtn.disabled = false;
      generateBtn.disabled = false;
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
      if (!data.running && pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
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
        duration: Number(duration.value || 30)
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

    runBtn.addEventListener("click", startRun);
    generateBtn.addEventListener("click", startGenerate);
    clearBtn.addEventListener("click", () => {
      terminal.textContent = "";
      nextIndex = 0;
    });

    pollLogs();
  </script>
</body>
</html>
"""


def add_log(text: str, kind: str = "") -> None:
    entry = {"text": text.rstrip("\n"), "kind": kind}
    LOG_QUEUE.put(entry)


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


def run_interview_set_generator(
    job_family: str,
    count: int,
    experience_range: str,
    question_mode: str,
    duration: int,
) -> None:
    global EXIT_CODE, RUNNING

    try:
        add_log("[UI] Starting AI interview set generator.", "meta")
        add_log(f"[UI] Job type: {job_family}", "meta")
        add_log(f"[UI] Role count: {count}", "meta")
        add_log(f"[UI] Experience range: {experience_range}", "meta")
        add_log(f"[UI] Question mode: {question_mode}", "meta")
        add_log(f"[UI] Duration: {duration} minutes", "meta")

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
                draft = build_draft(role, experience_range, question_mode, duration)
                print(f"\n[CREATE] Starting: {draft['title']}", flush=True)
                if create_one_interview_set(token, draft):
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


def clear_logs() -> None:
    LOGS.clear()
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

    with PROCESS_LOCK:
        if RUNNING:
            return False, "Another process is already running."

        RUNNING = True
        EXIT_CODE = None
        clear_logs()

    thread = threading.Thread(
        target=run_interview_set_generator,
        args=(job_family, count, experience_range, question_mode, duration),
        daemon=True,
    )
    thread.start()
    return True, "Started."


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
