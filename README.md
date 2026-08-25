# Live-job-crawler

A production-grade job crawler for **SRE / DevOps / Platform Engineer** roles.

## Features
- Crawls Remotive, Arbeitnow, We Work Remotely, Greenhouse (30 companies), Lever (15 companies), Google Search (SerpApi)
- Filter by role, job type (remote/onsite/hybrid), location, experience
- Continuous crawl mode — keeps running until stopped
- Live log streaming per crawl campaign
- Multi-tab UI with sorting options
- Dark production-grade UI

## Run with Docker

```bash
docker build -t job-crawler .
docker run -d -p 8000:8000 -e SERPAPI_KEY=your_key job-crawler
```

Open http://localhost:8000

## Stack
- FastAPI + SQLite (backend)
- BeautifulSoup + requests (crawler)
- Vanilla JS (frontend)
