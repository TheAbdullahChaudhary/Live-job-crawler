#!/bin/bash
# Docker run (recommended — data persists across restarts):
#   docker volume create job-crawler-data
#   docker run -d --name job-crawler --network host \
#     -v job-crawler-data:/app/data \
#     -e SERPAPI_KEY=your_key job-crawler

cd "$(dirname "$0")"

echo "Installing dependencies..."
pip install -r requirements.txt -q
playwright install chromium 2>/dev/null || true

mkdir -p data
echo "Initializing DB..."
cd backend && python -c "import db"

echo "Starting server at http://localhost:8000"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
