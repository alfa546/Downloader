import uuid
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from schemas import JobCreate, JobStatus
from redis_client import set_job_status, get_job_status
from tasks import download_video, finalize_video_task

from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")

# Set up CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/jobs", response_model=JobStatus)
def create_job(job_in: JobCreate):
    job_id = str(uuid.uuid4())
    url = str(job_in.url)
    
    # Initialize status in Redis
    set_job_status(job_id, "queued")
    
    # Queue the celery task
    download_video.delay(job_id, url, remove_watermark=job_in.remove_watermark)
    
    return {"job_id": job_id, "status": "queued"}

@app.get("/jobs/{job_id}/status", response_model=JobStatus)
def read_job_status(job_id: str):
    status_data = get_job_status(job_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Job not found")
        
    progress_str = status_data.get("progress")
    progress = float(progress_str) if progress_str is not None else None
    
    return {
        "job_id": job_id,
        "status": status_data.get("status", "unknown"),
        "progress": progress,
        "error": status_data.get("error")
    }

@app.post("/jobs/{job_id}/finalize")
def finalize_job(job_id: str, quality: str = Query(..., pattern="^(480p|720p|1080p|4k)$")):
    status_data = get_job_status(job_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if status_data.get("status") != "awaiting_quality_choice":
        raise HTTPException(status_code=400, detail="Job not ready for finalization")
        
    set_job_status(job_id, "queued_for_processing")
    
    finalize_video_task.delay(job_id, quality)
        
    return {"job_id": job_id, "status": "queued_for_processing"}

@app.get("/jobs/{job_id}/download")
def download_job(job_id: str):
    status_data = get_job_status(job_id)
    if not status_data or status_data.get("status") != "done":
        raise HTTPException(status_code=400, detail="File not ready")
        
    job_dir = settings.STORAGE_DIR / job_id
    final_path = job_dir / "final.mp4"
    
    if not final_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(path=final_path, filename=f"mediaforge_final.mp4", media_type='video/mp4')

# Serve static frontend files if built
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/dist"))
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{filename}")
    def get_static_file(filename: str):
        file_path = os.path.join(frontend_dist, filename)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        # Fallback to index.html for React routing
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    @app.get("/")
    def read_root_index():
        return FileResponse(os.path.join(frontend_dist, "index.html"))

@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
