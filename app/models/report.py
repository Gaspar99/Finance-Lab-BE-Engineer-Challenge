from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class ReportStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class ImageItem(BaseModel):
    url: str
    filename: str


class Report(BaseModel):
    id: str
    created_at: datetime
    status: ReportStatus
    patient: Optional[str] = None
    owner: Optional[str] = None
    veterinarian: Optional[str] = None
    diagnosis: Optional[str] = None
    recommendations: Optional[str] = None
    images: list[ImageItem] = []
    error: Optional[str] = None
    original_filename: str
