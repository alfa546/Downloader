import os
import cv2
import ffmpeg
from pathlib import Path
import glob
import time
import shutil
from redis_client import set_job_status

def upscale_video(input_path: Path, output_path: Path, job_id: str):
    # 1. Try to load Real-ESRGAN
    try:
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer
        
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        upsampler = RealESRGANer(
            scale=4,
            model_path='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth',
            model=model,
            half=False
        )
        use_mock = False
    except ImportError:
        use_mock = True

    if use_mock:
        # Fast path: instant FFmpeg upscale (2160p / 4K)
        print("Real-ESRGAN not available. Using fast FFmpeg 4K scaling...")
        set_job_status(job_id, "upscaling", progress=20)
        try:
            # Check if there is audio
            has_audio = False
            try:
                probe = ffmpeg.probe(str(input_path))
                has_audio = any(stream['codec_type'] == 'audio' for stream in probe.get('streams', []))
            except Exception:
                has_audio = True

            output_opts = {'vf': 'scale=3840:2160:flags=lanczos', 'vcodec': 'libx264'}
            if has_audio:
                output_opts['acodec'] = 'copy'
            else:
                output_opts['an'] = None

            (
                ffmpeg
                .input(str(input_path))
                .output(str(output_path), **output_opts)
                .overwrite_output()
                .run(quiet=True)
            )
            set_job_status(job_id, "upscaling", progress=100)
        except Exception as e:
            raise RuntimeError(f"Fast upscaling failed: {str(e)}")
        return

    # Real-ESRGAN path (slow frame extraction)
    job_dir = input_path.parent
    frames_dir = job_dir / "frames"
    upscaled_dir = job_dir / "upscaled_frames"
    frames_dir.mkdir(exist_ok=True)
    upscaled_dir.mkdir(exist_ok=True)
    
    try:
        (
            ffmpeg
            .input(str(input_path))
            .output(str(frames_dir / "frame_%04d.png"))
            .overwrite_output()
            .run(quiet=True)
        )
    except Exception as e:
        raise RuntimeError(f"Frame extraction failed: {str(e)}")
        
    frame_files = sorted(glob.glob(str(frames_dir / "*.png")))
    total_frames = len(frame_files)
    
    if total_frames == 0:
        raise RuntimeError("No frames extracted.")
        
    for i, frame_path in enumerate(frame_files):
        out_name = Path(frame_path).name
        out_path = upscaled_dir / out_name
        
        img = cv2.imread(frame_path)
        upscaled, _ = upsampler.enhance(img, outscale=4)
        cv2.imwrite(str(out_path), upscaled)
            
        progress = int(((i + 1) / total_frames) * 100)
        if progress % 5 == 0 or progress == 100:
            set_job_status(job_id, "upscaling", progress=progress)
            
    try:
        probe = ffmpeg.probe(str(input_path))
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        fps_str = video_info['r_frame_rate']
        
        has_audio = any(stream['codec_type'] == 'audio' for stream in probe.get('streams', []))
        
        video_in = ffmpeg.input(str(upscaled_dir / "frame_%04d.png"), framerate=fps_str)
        
        if has_audio:
            audio_in = ffmpeg.input(str(input_path))
            (
                ffmpeg
                .output(video_in, audio_in, str(output_path), vcodec='libx264', acodec='copy')
                .overwrite_output()
                .run(quiet=True)
            )
        else:
            (
                ffmpeg
                .output(video_in, str(output_path), vcodec='libx264')
                .overwrite_output()
                .run(quiet=True)
            )
    except Exception as e:
        raise RuntimeError(f"Reassembly failed: {str(e)}")
    finally:
        shutil.rmtree(frames_dir, ignore_errors=True)
        shutil.rmtree(upscaled_dir, ignore_errors=True)
