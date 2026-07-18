import cv2
import numpy as np
import ffmpeg
import os
from pathlib import Path
import shutil

# Basic configuration for watermark regions per platform
# Format: (x, y, width, height)
# For MVP, using static regions. In phase 2, ProPainter could handle dynamic/moving masks.
WATERMARK_REGIONS = {
    "tiktok": [
        (10, 10, 200, 50),     # Top-left assumption
        (500, 800, 200, 50)    # Bottom-right assumption (will be bounded by actual frame size)
    ],
    "instagram": [
        (10, 10, 200, 50)
    ],
    "youtube": [],
    "facebook": []
}

def remove_watermark(input_path: Path, output_path: Path, platform: str):
    regions = WATERMARK_REGIONS.get(platform, [])
    if not regions:
        # If no regions configured, just copy the file
        shutil.copy(str(input_path), str(output_path))
        return

    # Build FFmpeg delogo filter string
    delogo_filters = []
    for (x, y, w, h) in regions:
        delogo_filters.append(f"delogo=x={x}:y={y}:w={w}:h={h}")
    filter_graph = ",".join(delogo_filters)

    try:
        (
            ffmpeg
            .input(str(input_path))
            .output(str(output_path), vf=filter_graph, vcodec='libx264', acodec='copy')
            .overwrite_output()
            .run(quiet=True)
        )
    except Exception as e:
        print(f"FFmpeg delogo failed, using fallback copy: {e}")
        shutil.copy(str(input_path), str(output_path))
