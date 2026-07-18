from pydantic import BaseModel, HttpUrl, validator
from typing import Optional
from urllib.parse import urlparse

class JobCreate(BaseModel):
    url: HttpUrl
    remove_watermark: bool = True

    @validator('url')
    def validate_platform(cls, v):
        domain = urlparse(str(v)).netloc.lower()
        allowed_domains = ['instagram.com', 'tiktok.com', 'facebook.com', 'youtube.com', 'youtu.be']
        if not any(allowed in domain for allowed in allowed_domains):
            raise ValueError('Unsupported platform. Only Instagram, TikTok, Facebook, and YouTube are allowed.')
        return v

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: Optional[float] = None
    error: Optional[str] = None
