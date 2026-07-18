import os
# Inject Heroku FFmpeg binary path into system PATH at runtime
heroku_ffmpeg_path = "/app/vendor/ffmpeg/bin"
if os.path.exists(heroku_ffmpeg_path) and heroku_ffmpeg_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = heroku_ffmpeg_path + os.path.pathsep + os.environ.get("PATH", "")

import yt_dlp
from celery_app import celery_app
from config import settings
from redis_client import set_job_status
from urllib.parse import urlparse
from pathlib import Path
from watermark import remove_watermark
from upscale import upscale_video
import ffmpeg
import json

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
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': str(output_path),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': False,
        'retries': 3,
        'fragment_retries': 3,
        'socket_timeout': 30,
        'extractor_args': {
            'youtube': {
                'player_client': ['tvhtml5', 'ios', 'android']
            }
        }
    }
    
    # 1. Inject platform-specific Cookies if provided (100% bypass for datacenter bans)
    platform = get_platform(url)
    cookies_str = None
    if platform == 'youtube':
        cookies_str = os.getenv("YOUTUBE_COOKIES")
    elif platform == 'instagram':
        cookies_str = os.getenv("INSTAGRAM_COOKIES")
    elif platform == 'tiktok':
        cookies_str = os.getenv("TIKTOK_COOKIES")
        
    if cookies_str:
        cookies_path = job_dir / f"{platform}_cookies.txt"
        # Normalize line endings to Unix \n for Linux parser safety
        normalized_cookies = cookies_str.replace('\r\n', '\n').strip()
        cookies_path.write_text(normalized_cookies)
        ydl_opts['cookiefile'] = str(cookies_path)
    
    proxy = os.getenv("PROXY_URL")
    if proxy and not any(placeholder in proxy for placeholder in ["username", "password", "proxyserver.com", "example.com"]):
        ydl_opts['proxy'] = proxy
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        # Save job metadata for the single-pass finalizing step
        metadata = {
            "url": url,
            "remove_watermark": remove_watermark,
            "platform": get_platform(url)
        }
        with open(job_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)
            
        set_job_status(job_id, "awaiting_quality_choice")
    except Exception as e:
        set_job_status(job_id, "failed", error=str(e))
        raise e

@celery_app.task(bind=True)
def finalize_video_task(self, job_id: str, quality: str):
    job_dir = settings.STORAGE_DIR / job_id
    
    # Load metadata
    metadata_path = job_dir / "metadata.json"
    if not metadata_path.exists():
        set_job_status(job_id, "failed", error="Job metadata not found.")
        return
        
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
        
    remove_wm = metadata.get("remove_watermark", True)
    platform = metadata.get("platform", "unknown")
    
    raw_path = job_dir / "raw.mp4"
    final_path = job_dir / "final.mp4"
    
    try:
        if quality == "4k":
            set_job_status(job_id, "upscaling", progress=0)
            # If watermark removal is requested, remove it, then upscale
            if remove_wm:
                clean_path = job_dir / "clean.mp4"
                remove_watermark(raw_path, clean_path, platform)
                upscale_video(clean_path, final_path, job_id)
                if clean_path.exists():
                    os.remove(clean_path)
            else:
                upscale_video(raw_path, final_path, job_id)
            set_job_status(job_id, "done", progress=100)
        else:
            set_job_status(job_id, "resizing")
            heights = {
                "480p": 480,
                "720p": 720,
                "1080p": 1080
            }
            target_height = heights.get(quality, 720)
            
            # Check if delogo is configured for this platform
            from watermark import WATERMARK_REGIONS
            regions = WATERMARK_REGIONS.get(platform, [])
            
            # Combine delogo and scaling filter graph to avoid double encoding
            if remove_wm and regions:
                delogo_filters = []
                for (x, y, w, h) in regions:
                    delogo_filters.append(f"delogo=x={x}:y={y}:w={w}:h={h}")
                filter_graph = ",".join(delogo_filters) + f",scale=-2:{target_height}"
            else:
                filter_graph = f"scale=-2:{target_height}"
                
            (
                ffmpeg
                .input(str(raw_path))
                .output(str(final_path), vf=filter_graph, vcodec='libx264', acodec='copy')
                .overwrite_output()
                .run(quiet=True)
            )
            set_job_status(job_id, "done")
    except Exception as e:
        set_job_status(job_id, "failed", error=str(e))
        raise e
