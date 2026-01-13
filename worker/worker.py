import os
import time
import csv
from datetime import datetime
import requests

API_BASE = os.getenv("CONTROL_PLANE_API", "http://127.0.0.1:8000")
POLL_SECONDS = float(os.getenv("POLL_SECONDS", "2.0"))


def iso_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def get_sources():
    r = requests.get(f"{API_BASE}/sources", timeout=10)
    r.raise_for_status()
    return r.json()


def start_job_for_source(source_id: int):
    r = requests.post(f"{API_BASE}/sources/{source_id}/ingestions", timeout=10)
    r.raise_for_status()
    return r.json()


def get_job(job_id: int):
    r = requests.get(f"{API_BASE}/ingestions/{job_id}", timeout=10)
    r.raise_for_status()
    return r.json()


def get_pending_job(db_jobs):
    # placeholder helper if you later add /ingestions?status=QUEUED.
    return None


def post_event(job_id: int, type_: str, payload: dict):
    # We'll add these endpoints in api/main.py in the next step if missing
    r = requests.post(f"{API_BASE}/ingestions/{job_id}/events", json={"type": type_, "payload": payload}, timeout=10)
    r.raise_for_status()


def post_error(job_id: int, code: str, message: str, retryable: bool = True):
    r = requests.post(
        f"{API_BASE}/ingestions/{job_id}/errors",
        json={"code": code, "message": message, "retryable": retryable},
        timeout=10,
    )
    r.raise_for_status()


def patch_job(job_id: int, payload: dict):
    r = requests.patch(f"{API_BASE}/ingestions/{job_id}", json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def process_csv(job_id: int, csv_path: str):
    abs_path = csv_path
    if not os.path.isabs(abs_path):
        # resolve relative paths from project root
        abs_path = os.path.abspath(csv_path)

    if not os.path.exists(abs_path):
        post_error(job_id, "FILE_NOT_FOUND", f"CSV path not found: {abs_path}", retryable=False)
        patch_job(job_id, {"status": "FAILED", "finished_at": iso_now()})
        return

    patch_job(job_id, {"status": "RUNNING", "started_at": iso_now()})
    post_event(job_id, "JOB_STARTED", {"ts": iso_now(), "csv_path": abs_path})

    rows = 0
    with open(abs_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for _ in reader:
            rows += 1
            if rows % 2 == 0:
                post_event(job_id, "PROGRESS", {"ts": iso_now(), "rows_read": rows})
                patch_job(job_id, {"checkpoint": str(rows), "metrics": {"rows_read": rows}})

    post_event(job_id, "JOB_FINISHED", {"ts": iso_now(), "rows_read": rows})
    patch_job(job_id, {"status": "SUCCEEDED", "finished_at": iso_now(), "metrics": {"rows_read": rows}})


def main():
    print(f"Worker started. Polling {API_BASE} every {POLL_SECONDS}s ...")

    # For the simple MVP: pick the first source, start a job once if no jobs exist.
    # (You can upgrade to a real queue endpoint later.)
    sources = get_sources()
    if not sources:
        print("No sources found. Create one via POST /sources first.")
        return

    source_id = sources[0]["id"]
    print(f"Starting ingestion for source_id={source_id}")
    job = start_job_for_source(source_id)
    job_id = job["id"]

    # We need the source config (csv_path). For now we read it from env or assume ./data/sample.csv
    csv_path = os.getenv("CSV_PATH", "./data/sample.csv")
    process_csv(job_id, csv_path)

    print("Done.")


if __name__ == "__main__":
    main()
