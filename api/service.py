from sqlalchemy.orm import Session
from datetime import datetime
from . import models


def create_source(db: Session, name: str, csv_path: str):
    src = models.Source(
        name=name,
        config={"csv_path": csv_path},
        status="active",
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


def start_ingestion(db: Session, source_id: int):
    job = models.IngestionJob(
        source_id=source_id,
        status="QUEUED",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def log_event(db: Session, job_id: int, type: str, payload: dict):
    evt = models.IngestionEvent(
        job_id=job_id,
        type=type,
        payload=payload,
    )
    db.add(evt)
    db.commit()


def log_error(db: Session, job_id: int, code: str, message: str, retryable=True):
    err = models.IngestionError(
        job_id=job_id,
        severity="ERROR",
        code=code,
        message=message,
        details={},
        retryable=1 if retryable else 0,
    )
    db.add(err)
    db.commit()


def mark_job_running(db: Session, job):
    job.status = "RUNNING"
    job.started_at = datetime.utcnow()
    db.commit()


def mark_job_finished(db: Session, job, status="SUCCEEDED"):
    job.status = status
    job.finished_at = datetime.utcnow()
    db.commit()
