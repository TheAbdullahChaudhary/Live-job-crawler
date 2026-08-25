import sqlite3, os

DB = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "jobs.db"))
os.makedirs(os.path.dirname(DB), exist_ok=True)

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, company TEXT, location TEXT,
                experience_min INTEGER, experience_max INTEGER,
                job_type TEXT, url TEXT UNIQUE, posted_at TEXT,
                source TEXT, crawl_id TEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # migrations
        for col in ["source TEXT", "crawl_id TEXT"]:
            try: conn.execute(f"ALTER TABLE jobs ADD COLUMN {col}")
            except: pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                label TEXT, status TEXT, start_time TEXT,
                job_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

init_db()
