from __future__ import annotations

import json
import os
import threading
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

try:
    from .workbook_service import ProcessingConfig, load_excel_columns, process_excel
    from .path_utils import connect_to_share, normalize_datasheet_path
except ImportError:
    from workbook_service import ProcessingConfig, load_excel_columns, process_excel
    from path_utils import connect_to_share, normalize_datasheet_path


BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = Path(tempfile.gettempdir()) / "datasheets_scanner_runtime"
UPLOAD_DIR = RUNTIME_DIR / "uploads"
OUTPUT_DIR = RUNTIME_DIR / "outputs"
TASK_CONFIG_PATH = BASE_DIR / "config.json"

for directory in (UPLOAD_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB
app.secret_key = "datasheets-scanner-local-secret"


UPLOAD_SESSIONS: dict[str, dict] = {}
JOBS: dict[str, dict] = {}
STATE_LOCK = threading.Lock()


def load_task_prompt() -> str:
    try:
        data = json.loads(TASK_CONFIG_PATH.read_text(encoding="utf-8"))
        tasks = data.get("tasks", [])
        if tasks:
            return str(tasks[0].get("prompt", "")).strip()
    except Exception:
        pass
    return "Extract the operating temperature range from the datasheet text and return the exact source sentence."


def _set_job(job_id: str, **updates) -> None:
    with STATE_LOCK:
        JOBS.setdefault(job_id, {}).update(updates)


def _append_log(job_id: str, message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    with STATE_LOCK:
        job = JOBS.setdefault(job_id, {})
        job.setdefault("logs", []).append(f"[{timestamp}] {message}")


def _update_progress(job_id: str, current: int, total: int) -> None:
    percent = int((current / total) * 100) if total else 0
    with STATE_LOCK:
        job = JOBS.setdefault(job_id, {})
        job["current"] = current
        job["total"] = total
        job["progress"] = percent


def _run_job(job_id: str, config: ProcessingConfig) -> None:
    try:
        _set_job(job_id, status="running", started_at=datetime.now().isoformat())
        _append_log(job_id, "Job started")

        def log_cb(message: str) -> None:
            _append_log(job_id, message)

        def progress_cb(current: int, total: int) -> None:
            _update_progress(job_id, current, total)

        output_path = process_excel(config, progress_callback=progress_cb, log_callback=log_cb)
        _set_job(job_id, status="completed", output_path=output_path, finished_at=datetime.now().isoformat())
        _append_log(job_id, "Job completed successfully")
    except Exception as exc:
        _set_job(job_id, status="failed", error=str(exc), finished_at=datetime.now().isoformat())
        _append_log(job_id, f"Job failed: {exc}")


@app.get("/")
def index():
    token = request.args.get("token", "").strip()
    session = UPLOAD_SESSIONS.get(token) if token else None
    return render_template(
        "index.html",
        token=token,
        session=session,
        prompt=load_task_prompt(),
    )


@app.post("/upload")
def upload_excel():
    excel_file = request.files.get("excel_file")
    if not excel_file or not excel_file.filename:
        return render_template("index.html", error="Please choose an Excel file.", prompt=load_task_prompt())

    filename = secure_filename(excel_file.filename)
    if not filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
        return render_template("index.html", error="Please upload an Excel file.", prompt=load_task_prompt())

    token = uuid.uuid4().hex
    token_dir = UPLOAD_DIR / token
    token_dir.mkdir(parents=True, exist_ok=True)
    saved_path = token_dir / filename
    excel_file.save(saved_path)

    try:
        columns = load_excel_columns(str(saved_path))
    except Exception as exc:
        return render_template("index.html", error=f"Could not read Excel file: {exc}", prompt=load_task_prompt())

    UPLOAD_SESSIONS[token] = {
        "file_path": str(saved_path),
        "file_name": filename,
        "columns": columns,
    }

    return redirect(url_for("index", token=token))


@app.post("/process")
def process():
    token = request.form.get("token", "").strip()
    session = UPLOAD_SESSIONS.get(token)
    if not session:
        return render_template("index.html", error="Upload an Excel file first.", prompt=load_task_prompt())

    datasheet_column = request.form.get("datasheet_column", "").strip()
    unique_id_column = request.form.get("unique_id_column", "").strip()
    drive_letter = request.form.get("drive_letter", "").strip()
    network_root = request.form.get("network_root", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    domain = request.form.get("domain", "").strip()
    model = request.form.get("model", "llama3.1").strip() or "llama3.1"

    if not datasheet_column or not unique_id_column:
        return render_template(
            "index.html",
            token=token,
            session=session,
            error="Select both the datasheet path column and the unique ID column.",
            prompt=load_task_prompt(),
        )

    job_id = uuid.uuid4().hex
    output_dir = OUTPUT_DIR / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = f"{Path(session['file_name']).stem}_datasheet_scanned.xlsx"
    output_path = output_dir / output_name

    config = ProcessingConfig(
        input_excel=session["file_path"],
        output_excel=str(output_path),
        datasheet_column=datasheet_column,
        unique_id_column=unique_id_column,
        drive_letter=drive_letter,
        network_root=network_root,
        username=username,
        password=password,
        domain=domain,
        model=model,
        prompt=load_task_prompt(),
    )

    with STATE_LOCK:
        JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "current": 0,
            "total": 0,
            "logs": ["Job queued"],
            "output_path": str(output_path),
        }

    thread = threading.Thread(target=_run_job, args=(job_id, config), daemon=True)
    thread.start()
    return redirect(url_for("job_page", job_id=job_id))


@app.post("/api/check-share")
def api_check_share():
    payload = request.get_json(silent=True) or {}

    network_root = str(payload.get("network_root", "") or "").strip()
    username = str(payload.get("username", "") or "").strip()
    password = str(payload.get("password", "") or "").strip()
    domain = str(payload.get("domain", "") or "").strip()
    drive_letter = str(payload.get("drive_letter", "") or "").strip()
    sample_path = str(payload.get("sample_path", "") or "").strip()

    if not network_root:
        return jsonify({"ok": False, "message": "Enter a network UNC root first (example: \\\\server\\share)."}), 400

    ok, message = connect_to_share(network_root, username=username, password=password, domain=domain)
    if not ok:
        return jsonify({"ok": False, "message": message}), 200

    response = {
        "ok": True,
        "message": message,
        "normalized_path": "",
        "path_exists": None,
    }

    if sample_path:
        normalized = normalize_datasheet_path(sample_path, drive_letter, network_root)
        exists = Path(normalized).exists()
        response["normalized_path"] = normalized
        response["path_exists"] = exists
        if not exists:
            response["message"] = f"Share auth passed, but sample path was not found: {normalized}"

    return jsonify(response), 200


@app.get("/job/<job_id>")
def job_page(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return render_template("job.html", error="Job not found.", job_id=job_id)
    return render_template("job.html", job=job, job_id=job_id)


@app.get("/api/job/<job_id>")
def api_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.get("/download/<job_id>")
def download(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return render_template("job.html", error="Job not found.", job_id=job_id), 404
    output_path = job.get("output_path")
    if not output_path or not Path(output_path).exists():
        return render_template("job.html", error="Output file is not ready yet.", job_id=job_id), 404
    return send_file(output_path, as_attachment=True)


if __name__ == "__main__":
    host = os.environ.get("DATASHEET_SCANNER_HOST", "127.0.0.1")
    port = int(os.environ.get("DATASHEET_SCANNER_PORT", "5000"))
    app.run(host=host, port=port, debug=False)
