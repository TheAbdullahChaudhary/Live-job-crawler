import sys, os, threading
sys.path.insert(0, os.path.dirname(__file__))
from db import get_conn
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import subprocess, queue, json, time

app = FastAPI()

crawl_queues: dict[str, queue.Queue] = {}
crawl_stop_flags: dict[str, bool] = {}

@app.get("/api/jobs")
def get_jobs(
    role: str = Query(None),
    experience: int = Query(None),
    job_type: str = Query(None),
    location: str = Query(None),
    sort: str = Query("newest", description="newest|oldest|exp_asc|exp_desc|company"),
):
    conn = get_conn()
    q = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if role:
        q += " AND LOWER(title) LIKE ?"
        params.append(f"%{role.lower()}%")
    if job_type:
        q += " AND job_type = ?"
        params.append(job_type.lower())
    if location:
        q += " AND LOWER(location) LIKE ?"
        params.append(f"%{location.lower()}%")
    if experience is not None:
        q += " AND (experience_max IS NULL OR experience_max <= ?)"
        params.append(experience)

    order = {
        "newest":   "crawled_at DESC",
        "oldest":   "crawled_at ASC",
        "exp_asc":  "experience_min ASC NULLS LAST",
        "exp_desc": "experience_max DESC NULLS LAST",
        "company":  "company ASC",
    }.get(sort, "crawled_at DESC")
    q += f" ORDER BY {order}"

    return [dict(r) for r in conn.execute(q, params).fetchall()]

@app.post("/api/crawl")
def trigger_crawl(
    sources: str = Query("all"),
    continuous: bool = Query(False),
):
    crawl_id = f"crawl_{int(time.time())}"
    q: queue.Queue = queue.Queue()
    crawl_queues[crawl_id] = q
    crawl_stop_flags[crawl_id] = False

    def run():
        env = os.environ.copy()
        env["CRAWL_SOURCES"] = sources
        run_count = 0
        while True:
            run_count += 1
            if continuous:
                q.put(f"=== Run #{run_count} started ===")
            proc = subprocess.Popen(
                [sys.executable, "crawler/crawler.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=env
            )
            for line in proc.stdout:
                if crawl_stop_flags.get(crawl_id):
                    proc.terminate()
                    break
                q.put(line.rstrip())
            proc.wait()

            if not continuous or crawl_stop_flags.get(crawl_id):
                break

            q.put(f"__RUN_DONE__{run_count}")
            # no sleep — start next run immediately

        q.put("__DONE__")
        crawl_stop_flags.pop(crawl_id, None)

    threading.Thread(target=run, daemon=True).start()
    return {"crawl_id": crawl_id}

@app.post("/api/crawl/stop/{crawl_id}")
def stop_crawl(crawl_id: str):
    crawl_stop_flags[crawl_id] = True
    return {"status": "stopping"}

@app.get("/api/crawl/stream/{crawl_id}")
def stream_crawl(crawl_id: str):
    q = crawl_queues.get(crawl_id)
    if not q:
        return {"error": "invalid crawl_id"}
    def generate():
        while True:
            line = q.get()
            yield f"data: {json.dumps(line)}\n\n"
            if line == "__DONE__":
                crawl_queues.pop(crawl_id, None)
                break
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.delete("/api/jobs")
def delete_all_jobs():
    conn = get_conn()
    conn.execute("DELETE FROM jobs")
    conn.commit()
    return {"deleted": "all"}

@app.delete("/api/jobs/selected")
def delete_selected_jobs(ids: str = Query(..., description="comma-separated job ids")):
    conn = get_conn()
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()]
    conn.execute(f"DELETE FROM jobs WHERE id IN ({','.join('?'*len(id_list))})", id_list)
    conn.commit()
    return {"deleted": len(id_list)}

@app.get("/api/stats")
def stats():
    conn = get_conn()
    total    = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    by_type  = dict(conn.execute("SELECT job_type, COUNT(*) FROM jobs GROUP BY job_type").fetchall())
    by_co    = dict(conn.execute("SELECT company, COUNT(*) FROM jobs GROUP BY company ORDER BY COUNT(*) DESC LIMIT 5").fetchall())
    return {"total": total, "by_type": by_type, "top_companies": by_co}

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
