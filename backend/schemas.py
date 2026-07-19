from pydantic import BaseModel, HttpUrl
from typing import Optional


class JobCreate(BaseModel):
    url: HttpUrl
    remove_watermark: bool = True


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: Optional[float] = None
    error: Optional[str] = None
