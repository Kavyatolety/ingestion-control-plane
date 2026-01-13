from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, default="csv")
    config = Column(JSON, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    ingestions = relationship("IngestionJob", back_populates="source")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    status = Column(String, default="QUEUED")
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    checkpoint = Column(String)
    metrics = Column(JSON, default={})

    source = relationship("Source", back_populates="ingestions")
    events = relationship("IngestionEvent", back_populates="job")
    errors = relationship("IngestionError", back_populates="job")


class IngestionEvent(Base):
    __tablename__ = "ingestion_events"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("ingestion_jobs.id"))
    ts = Column(DateTime, default=datetime.utcnow)
    type = Column(String)
    payload = Column(JSON)

    job = relationship("IngestionJob", back_populates="events")


class IngestionError(Base):
    __tablename__ = "ingestion_errors"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("ingestion_jobs.id"))
    ts = Column(DateTime, default=datetime.utcnow)
    severity = Column(String)
    code = Column(String)
    message = Column(String)
    details = Column(JSON)
    retryable = Column(Integer, default=1)

    job = relationship("IngestionJob", back_populates="errors")
