from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class SourceCreate(BaseModel):
    name: str
    csv_path: str


class SourceOut(BaseModel):
    id: int
    name: str
    status: str

    class Config:
        orm_mode = True


class JobOut(BaseModel):
    id: int
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    checkpoint: Optional[str]

    class Config:
        orm_mode = True


class EventOut(BaseModel):
    ts: datetime
    type: str
    payload: Dict


class ErrorOut(BaseModel):
    ts: datetime
    severity: str
    code: str
    message: str
    retryable: bool
