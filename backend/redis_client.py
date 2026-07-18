import sqlite3
from config import settings
import json
import os

DB_PATH = settings.STORAGE_DIR / "job_status.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jobs
                 (job_id TEXT PRIMARY KEY, status TEXT, error TEXT, progress INTEGER)''')
    conn.commit()
    conn.close()

init_db()

def set_job_status(job_id: str, status: str, error: str = None, progress: int = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if exists
    c.execute("SELECT status, error, progress FROM jobs WHERE job_id=?", (job_id,))
    row = c.fetchone()
    
    if row:
        new_status = status
        new_error = error if error is not None else row[1]
        new_progress = progress if progress is not None else row[2]
        c.execute("UPDATE jobs SET status=?, error=?, progress=? WHERE job_id=?", 
                  (new_status, new_error, new_progress, job_id))
    else:
        c.execute("INSERT INTO jobs (job_id, status, error, progress) VALUES (?, ?, ?, ?)",
                  (job_id, status, error, progress))
                  
    conn.commit()
    conn.close()

def get_job_status(job_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status, error, progress FROM jobs WHERE job_id=?", (job_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            "status": row[0],
            "error": row[1],
            "progress": row[2]
        }
    return {}
