import sys, os, threading
sys.path.insert(0, os.path.dirname(__file__))
from db import get_conn
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, Response
import subprocess, queue, json, time

app = FastAPI()

@app.get("/", include_in_schema=False)
def root():
    with open("frontend/index.html", "rb") as f:
        content = f.read()
    return Response(content, media_type="text/html", headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache", "Expires": "0"
    })

crawl_queues: dict[str, queue.Queue] = {}
crawl_stop_flags: dict[str, bool] = {}

@app.get("/api/jobs")
def get_jobs(
    role: str = Query(None),
    experience: int = Query(None),
    job_type: str = Query(None),
    location: str = Query(None),
    crawl_id: str = Query(None),
    sort: str = Query("newest"),
    days: int = Query(None),
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
    if crawl_id:
        q += " AND crawl_id = ?"
        params.append(crawl_id)
    if experience is not None:
        q += " AND experience_min IS NOT NULL AND experience_min <= ?"
        params.append(experience)
    if days is not None:
        q += " AND crawled_at >= date('now', ?)"
        params.append(f"-{days} days")

    order = {
        "newest":      "crawled_at DESC",
        "oldest":      "crawled_at ASC",
        "exp_asc":     "experience_min ASC NULLS LAST",
        "exp_desc":    "experience_max DESC NULLS LAST",
        "posted_desc": "posted_at DESC NULLS LAST",
        "posted_asc":  "posted_at ASC NULLS LAST",
        "company":     "company ASC",
    }.get(sort, "crawled_at DESC")
    q += f" ORDER BY {order}"

    return [dict(r) for r in conn.execute(q, params).fetchall()]

@app.post("/api/crawl")
def trigger_crawl(
    sources: str = Query("all"),
    continuous: bool = Query(False),
    interval: int = Query(0),
    experience: str = Query(None),
    locations: str = Query(None),
    role: str = Query(None),
    serpapi_key: str = Query(None),
):
    crawl_id = f"crawl_{int(time.time())}"
    q: queue.Queue = queue.Queue()
    crawl_queues[crawl_id] = q
    crawl_stop_flags[crawl_id] = False

    def run():
        env = os.environ.copy()
        env["CRAWL_SOURCES"] = sources
        env["DB_PATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "jobs.db"))
        env["CRAWL_ID"] = crawl_id
        if experience:  env["CRAWL_EXP"]  = experience
        if locations:   env["CRAWL_LOCS"] = locations
        if role:        env["CRAWL_ROLE"] = role
        if serpapi_key: env["SERPAPI_KEY"] = serpapi_key
        run_count = 0
        deadline = time.time() + interval * 60 if (continuous and interval > 0) else None
        while True:
            run_count += 1
            if continuous:
                remaining = max(0, int(deadline - time.time())) if deadline else 0
                q.put(f"=== Run #{run_count} | {remaining//60}m {remaining%60}s remaining ===")
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
            q.put(f"__RUN_DONE__{run_count}")

            if not continuous or crawl_stop_flags.get(crawl_id):
                break
            if deadline and time.time() >= deadline:
                q.put("⏹ Time limit reached, stopping.")
                break

        q.put("__DONE__")
        crawl_stop_flags.pop(crawl_id, None)

    threading.Thread(target=run, daemon=True).start()
    return {"crawl_id": crawl_id}

@app.get("/api/crawl/active")
def active_crawls():
    return {"active": [cid for cid, stopped in crawl_stop_flags.items() if not stopped]}

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

@app.get("/api/campaigns")
def list_campaigns():
    conn = get_conn()
    # mark any still-running as stopped (server restarted)
    conn.execute("UPDATE campaigns SET status='stopped' WHERE status='running'")
    conn.commit()
    return [dict(r) for r in conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC").fetchall()]

@app.post("/api/campaigns")
def save_campaign(id: str = Query(...), label: str = Query(...), status: str = Query(...), start_time: str = Query(...), job_count: int = Query(0)):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO campaigns (id,label,status,start_time,job_count) VALUES (?,?,?,?,?)",
                 (id, label, status, start_time, job_count))
    conn.commit()
    return {"ok": True}

@app.patch("/api/campaigns/{cid}")
def update_campaign(cid: str, status: str = Query(None), job_count: int = Query(None)):
    conn = get_conn()
    if status is not None:
        conn.execute("UPDATE campaigns SET status=? WHERE id=?", (status, cid))
    if job_count is not None:
        conn.execute("UPDATE campaigns SET job_count=? WHERE id=?", (job_count, cid))
    conn.commit()
    return {"ok": True}

@app.delete("/api/campaigns/{cid}")
def delete_campaign(cid: str):
    conn = get_conn()
    conn.execute("DELETE FROM campaigns WHERE id=?", (cid,))
    conn.commit()
    return {"ok": True}

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
    rows = conn.execute("""
        SELECT
          COUNT(*) as total,
          SUM(job_type='remote') as remote,
          SUM(job_type='onsite') as onsite,
          SUM(job_type='hybrid') as hybrid
        FROM jobs
    """).fetchone()
    src_rows = conn.execute("SELECT source, COUNT(*) as cnt FROM jobs WHERE source IS NOT NULL GROUP BY source ORDER BY cnt DESC").fetchall()
    by_source = {r[0]: r[1] for r in src_rows}
    return {"total": rows[0], "remote": rows[1] or 0, "onsite": rows[2] or 0, "hybrid": rows[3] or 0, "by_source": by_source}

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
