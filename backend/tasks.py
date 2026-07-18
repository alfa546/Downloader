import yt_dlp
from celery_app import celery_app
from config import settings
from redis_client import set_job_status
import os
from urllib.parse import urlparse
from pathlib import Path
from watermark import remove_watermark
from upscale import upscale_video
import ffmpeg

def get_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if 'tiktok.com' in domain: return 'tiktok'
    if 'instagram.com' in domain: return 'instagram'
    if 'facebook.com' in domain: return 'facebook'
    if 'youtube.com' in domain or 'youtu.be' in domain: return 'youtube'
    return 'unknown'

import shutil

@celery_app.task(bind=True)
def download_video(self, job_id: str, url: str, remove_watermark: bool = True):
    set_job_status(job_id, "downloading")
    
    job_dir = settings.STORAGE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = job_dir / "raw.mp4"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': str(output_path),
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'retries': 3,
        'fragment_retries': 3,
        'socket_timeout': 30,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        platform = get_platform(url)
        if remove_watermark:
            remove_watermark_task.delay(job_id, platform)
        else:
            raw_path = job_dir / "raw.mp4"
            clean_path = job_dir / "clean.mp4"
            shutil.copy(str(raw_path), str(clean_path))
            set_job_status(job_id, "awaiting_quality_choice")
    except Exception as e:
        set_job_status(job_id, "failed", error=str(e))
        raise e

@celery_app.task(bind=True)
def remove_watermark_task(self, job_id: str, platform: str):
    set_job_status(job_id, "removing_watermark")
    
    job_dir = settings.STORAGE_DIR / job_id
    raw_path = job_dir / "raw.mp4"
    clean_path = job_dir / "clean.mp4"
    
    try:
        remove_watermark(raw_path, clean_path, platform)
        set_job_status(job_id, "awaiting_quality_choice")
    except Exception as e:
        set_job_status(job_id, "failed", error=f"Watermark removal failed: {str(e)}")
        raise e

@celery_app.task(bind=True)
def resize_task(self, job_id: str, quality: str):
    set_job_status(job_id, "resizing")
    
    job_dir = settings.STORAGE_DIR / job_id
    clean_path = job_dir / "clean.mp4"
    final_path = job_dir / "final.mp4"
    
    heights = {
        "480p": 480,
        "720p": 720,
        "1080p": 1080
    }
    target_height = heights.get(quality, 720)
    
    try:
        (
            ffmpeg
            .input(str(clean_path))
            .output(str(final_path), vf=f'scale=-2:{target_height}', vcodec='libx264', acodec='copy')
            .overwrite_output()
            .run(quiet=True)
        )
        set_job_status(job_id, "done")
    except Exception as e:
        set_job_status(job_id, "failed", error=f"Resizing failed: {str(e)}")
        raise e

@celery_app.task(bind=True)
def upscale_4k_task(self, job_id: str):
    set_job_status(job_id, "upscaling", progress=0)
    job_dir = settings.STORAGE_DIR / job_id
    clean_path = job_dir / "clean.mp4"
    final_path = job_dir / "final.mp4"
    try:
        upscale_video(clean_path, final_path, job_id)
        set_job_status(job_id, "done", progress=100)
    except Exception as e:
        set_job_status(job_id, "failed", error=f"4K Upscaling failed: {str(e)}")
        raise e
