# ⚡ HeroDownloader

A lightning-fast, world-class video downloader with a premium dark glassmorphism UI. Download, clean, and upscale videos from YouTube, TikTok, Instagram, and Facebook — in seconds.

## ✨ Features

- **Instant Video Downloads** — Single-file pre-merged MP4 format for maximum speed
- **Watermark Removal** — FFmpeg-powered delogo filter (optional toggle)
- **Quality Selection** — 480p, 720p, 1080p, or AI 4K Upscale
- **Real-time Progress Stepper** — Live visual checklist of each processing stage
- **In-browser Video Preview** — Watch before downloading
- **Mobile Responsive** — Pixel-perfect on any screen size
- **Premium Dark UI** — Glassmorphism, animated gradients, micro-animations

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Vite |
| Backend | FastAPI + Python |
| Task Queue | Celery + SQLite Broker |
| Video Engine | yt-dlp + FFmpeg |
| Icons | Lucide React |

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- FFmpeg (auto-bundled via `imageio-ffmpeg`)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python -m pip install imageio-ffmpeg
```

### Run (2 terminals)

**Terminal 1 — API Server:**
```bash
cd backend
python main.py
```

**Terminal 2 — Celery Worker:**
```bash
cd backend
python -m celery -A celery_app worker --loglevel=info --pool=solo
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

## 📱 Supported Platforms

- YouTube
- TikTok
- Instagram
- Facebook

## 📄 License

MIT
