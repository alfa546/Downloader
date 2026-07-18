#!/bin/bash
# Start Celery worker in background using solo pool (recommended for Heroku single-dyno setup)
python -m celery -A celery_app worker --loglevel=info --pool=solo &

# Start FastAPI web server
uvicorn main:app --host 0.0.0.0 --port $PORT
