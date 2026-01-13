from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .db import get_db, engine
from .models import Base, Source, IngestionJob, IngestionEvent, IngestionError
from .schemas import SourceCreate, SourceOut, JobOut, EventOut, ErrorOut
from .service import create_source, start_ingestion

from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
from .service import log_event, log_error
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Ingestion Control Plane")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)


# -----------------------
# Sources
# -----------------------
@app.get("/sources", response_model=List[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).order_by(Source.id.asc()).all()
    # Return minimal fields expected by SourceOut
    return [{"id": s.id, "name": s.name, "status": s.status} for s in sources]


@app.post("/sources", response_model=SourceOut)
def create_source_endpoint(body: SourceCreate, db: Session = Depends(get_db)):
    # your schema uses csv_path, we store it in config["csv_path"]
    src = create_source(db, name=body.name, csv_path=body.csv_path)
    return {"id": src.id, "name": src.name, "status": src.status}


@app.get("/sources/{source_id}", response_model=SourceOut)
def get_source(source_id: int, db: Session = Depends(get_db)):
    src = db.query(Source).filter(Source.id == source_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    return {"id": src.id, "name": src.name, "status": src.status}


# -----------------------
# Ingestions (Jobs)
# -----------------------
@app.post("/sources/{source_id}/ingestions", response_model=JobOut)
def start_ingestion_endpoint(source_id: int, db: Session = Depends(get_db)):
    src = db.query(Source).filter(Source.id == source_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    if src.status != "active":
        raise HTTPException(status_code=409, detail="Source not active")

    job = start_ingestion(db, source_id=source_id)
    return {
        "id": job.id,
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "checkpoint": job.checkpoint,
    }


@app.get("/ingestions/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "checkpoint": job.checkpoint,
    }


@app.get("/ingestions/{job_id}/events", response_model=List[EventOut])
def get_job_events(job_id: int, db: Session = Depends(get_db)):
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    events = (
        db.query(IngestionEvent)
        .filter(IngestionEvent.job_id == job_id)
        .order_by(IngestionEvent.id.asc())
        .all()
    )

    return [{"ts": e.ts, "type": e.type, "payload": (e.payload or {})} for e in events]


@app.get("/ingestions/{job_id}/errors", response_model=List[ErrorOut])
def get_job_errors(job_id: int, db: Session = Depends(get_db)):
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    errors = (
        db.query(IngestionError)
        .filter(IngestionError.job_id == job_id)
        .order_by(IngestionError.id.asc()) 
        .all()
    )

    return [
        {
            "ts": e.ts,
            "severity": e.severity,
            "code": e.code,
            "message": e.message,
            "retryable": bool(e.retryable),
        }
        for e in errors
    ]

class EventIn(BaseModel):
    type: str
    payload: Dict[str, Any]

class ErrorIn(BaseModel):
    code: str
    message: str
    retryable: bool = True

class JobPatch(BaseModel):
    status: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    checkpoint: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None

@app.post("/ingestions/{job_id}/events")
def create_event(job_id: int, body: EventIn, db: Session = Depends(get_db)):
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    log_event(db, job_id=job_id, type=body.type, payload=body.payload)
    return {"ok": True}

@app.post("/ingestions/{job_id}/errors")
def create_error(job_id: int, body: ErrorIn, db: Session = Depends(get_db)):
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    log_error(db, job_id=job_id, code=body.code, message=body.message, retryable=body.retryable)
    return {"ok": True}

@app.patch("/ingestions/{job_id}", response_model=JobOut)
def patch_job(job_id: int, body: JobPatch, db: Session = Depends(get_db)):
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if body.status is not None:
        job.status = body.status
    if body.started_at is not None:
        job.started_at = datetime.fromisoformat(body.started_at.replace("Z", ""))
    if body.finished_at is not None:
        job.finished_at = datetime.fromisoformat(body.finished_at.replace("Z", ""))
    if body.checkpoint is not None:
        job.checkpoint = body.checkpoint
    if body.metrics is not None:
        job.metrics = body.metrics

    db.commit()
    db.refresh(job)
    return {
        "id": job.id,
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "checkpoint": job.checkpoint,
    }
