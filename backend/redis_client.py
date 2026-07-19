import sqlite3
from config import settings
import json
import os

# Check if Redis URL is available (e.g. on Heroku)
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL")
use_redis = REDIS_URL and REDIS_URL.startswith("redis")

if use_redis:
    import redis
    # Connect to Redis instance
    r = redis.from_url(REDIS_URL, decode_responses=True)
else:
    DB_PATH = settings.STORAGE_DIR / "job_status.db"

    def init_db():
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS jobs
                     (job_id TEXT PRIMARY KEY, status TEXT, error TEXT, progress INTEGER, media_type TEXT)''')
        try:
            c.execute("ALTER TABLE jobs ADD COLUMN media_type TEXT")
        except sqlite3.OperationalError:
            pass
        conn.commit()
        conn.close()

    init_db()

def set_job_status(job_id: str, status: str, error: str = None, progress: int = None, media_type: str = None):
    if use_redis:
        data = {
            "status": status,
            "error": error or "",
            "progress": str(progress) if progress is not None else "",
            "media_type": media_type or ""
        }
        existing = r.hgetall(f"job:{job_id}")
        if existing:
            if error is None: data["error"] = existing.get("error", "")
            if progress is None: data["progress"] = existing.get("progress", "")
            if media_type is None: data["media_type"] = existing.get("media_type", "")
        r.hmset(f"job:{job_id}", data)
    else:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT status, error, progress, media_type FROM jobs WHERE job_id=?", (job_id,))
        row = c.fetchone()
        
        if row:
            new_status = status
            new_error = error if error is not None else row[1]
            new_progress = progress if progress is not None else row[2]
            new_media_type = media_type if media_type is not None else row[3]
            c.execute("UPDATE jobs SET status=?, error=?, progress=?, media_type=? WHERE job_id=?", 
                      (new_status, new_error, new_progress, new_media_type, job_id))
        else:
            c.execute("INSERT INTO jobs (job_id, status, error, progress, media_type) VALUES (?, ?, ?, ?, ?)",
                      (job_id, status, error, progress, media_type))
                      
        conn.commit()
        conn.close()

def get_job_status(job_id: str) -> dict:
    if use_redis:
        data = r.hgetall(f"job:{job_id}")
        if not data:
            return {}
        return {
            "status": data.get("status"),
            "error": data.get("error") or None,
            "progress": int(data.get("progress")) if data.get("progress") else None,
            "media_type": data.get("media_type") or None
        }
    else:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT status, error, progress, media_type FROM jobs WHERE job_id=?", (job_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            return {
                "status": row[0],
                "error": row[1],
                "progress": row[2],
                "media_type": row[3]
            }
        return {}
