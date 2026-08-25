#!/bin/bash
cd "$(dirname "$0")"

echo "Installing dependencies..."
pip install -r requirements.txt -q
playwright install chromium 2>/dev/null || true

echo "Initializing DB..."
cd backend && python -c "import db"

echo "Starting server at http://localhost:8000"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
