import requests
from bs4 import BeautifulSoup
import sqlite3, re, os, time

DB = os.path.join(os.path.dirname(__file__), "..", "jobs.db")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}

# Set your SerpApi key here or via env var SERPAPI_KEY (free: serpapi.com)
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")

TARGET_ROLES = ["site reliability", "sre", "devops", "platform engineer", "infrastructure engineer"]

GREENHOUSE_COMPANIES = [
    # Cloud & Infra
    "cloudflare", "hashicorp", "datadog", "gitlab", "mongodb",
    "elastic", "confluent", "grafana", "pagerduty", "snyk",
    "github", "shopify", "airbnb", "uber", "lyft",
    "figma", "notion", "linear", "vercel", "stripe",
    "discord", "dropbox", "twilio", "okta", "splunk",
    "newrelic", "dynatrace", "sumologic", "lacework", "wiz-io",
    # More tech
    "squarespace", "hubspot", "zendesk", "intercom", "segment",
    "mixpanel", "amplitude", "braze", "contentful", "algolia",
    "fastly", "cloudinary", "auth0", "1password", "tailscale",
    "planetscale", "neon", "supabase", "render", "railway",
    "samsara", "verkada", "scale-ai", "weights-biases", "huggingface",
]

LEVER_COMPANIES = [
    "netflix", "pinterest", "reddit", "robinhood", "coinbase",
    "plaid", "brex", "rippling", "airtable", "retool",
    "anduril", "benchling", "carta", "gusto", "lattice",
    "loom", "mercury", "ramp", "deel", "remote",
    "dbt-labs", "airbyte", "prefect", "dagster", "meltano",
]

# ── helpers ───────────────────────────────────────────────────────────────────

def is_target_role(title: str) -> bool:
    return any(r in title.lower() for r in TARGET_ROLES)

def extract_experience(text: str):
    m = re.search(r'(\d+)\s*[-–to]+\s*(\d+)\s*years?', text, re.I)
    if m: return int(m.group(1)), int(m.group(2))
    m = re.search(r'(\d+)\+?\s*years?', text, re.I)
    if m: v = int(m.group(1)); return v, v
    return None, None

def extract_job_type(text: str) -> str:
    t = text.lower()
    if "remote" in t: return "remote"
    if "hybrid" in t: return "hybrid"
    if "onsite" in t or "on-site" in t: return "onsite"
    return "unknown"

def save_job(job: dict):
    try:
        with sqlite3.connect(DB) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO jobs
                (title, company, location, experience_min, experience_max, job_type, url, posted_at)
                VALUES (:title, :company, :location, :experience_min, :experience_max, :job_type, :url, :posted_at)
            """, job)
    except Exception as e:
        print(f"DB error: {e}")

# ── Remotive ──────────────────────────────────────────────────────────────────

def crawl_remotive():
    print("Crawling Remotive...")
    for category in ["devops-sysadmin", "software-dev"]:
        try:
            data = requests.get(f"https://remotive.com/api/remote-jobs?category={category}&limit=100", timeout=15).json()
            for j in data.get("jobs", []):
                title = j.get("title", "")
                if not is_target_role(title): continue
                text = BeautifulSoup(j.get("description", ""), "html.parser").get_text()
                exp_min, exp_max = extract_experience(text)
                save_job({"title": title, "company": j.get("company_name", ""),
                    "location": j.get("candidate_required_location", "Remote"),
                    "experience_min": exp_min, "experience_max": exp_max,
                    "job_type": "remote", "url": j.get("url", ""),
                    "posted_at": j.get("publication_date", "")})
                print(f"  [Remotive] {title}")
        except Exception as e:
            print(f"Remotive error: {e}")

# ── Arbeitnow ─────────────────────────────────────────────────────────────────

def crawl_arbeitnow():
    print("Crawling Arbeitnow...")
    try:
        data = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=15).json()
        for j in data.get("data", []):
            title = j.get("title", "")
            if not is_target_role(title): continue
            text = BeautifulSoup(j.get("description", ""), "html.parser").get_text()
            exp_min, exp_max = extract_experience(text)
            location = j.get("location", "")
            save_job({"title": title, "company": j.get("company_name", ""),
                "location": location, "experience_min": exp_min, "experience_max": exp_max,
                "job_type": "remote" if j.get("remote") else extract_job_type(location),
                "url": j.get("url", ""), "posted_at": ""})
            print(f"  [Arbeitnow] {title}")
    except Exception as e:
        print(f"Arbeitnow error: {e}")

# ── We Work Remotely RSS ──────────────────────────────────────────────────────

def crawl_weworkremotely():
    print("Crawling We Work Remotely...")
    feeds = [
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
        "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    ]
    for feed_url in feeds:
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml-xml")
            for item in soup.find_all("item"):
                raw_title = item.find("title").get_text(strip=True) if item.find("title") else ""
                # WWR format: "Company: Job Title"
                if ": " in raw_title:
                    company, title = raw_title.split(": ", 1)
                else:
                    company, title = "Unknown", raw_title
                if not is_target_role(title): continue
                url = item.find("link").get_text(strip=True) if item.find("link") else ""
                region_el = item.find("region")
                location = region_el.get_text(strip=True) if region_el else "Remote"
                desc = item.find("description")
                text = BeautifulSoup(desc.get_text(), "html.parser").get_text() if desc else ""
                exp_min, exp_max = extract_experience(text)
                save_job({"title": title, "company": company, "location": location,
                    "experience_min": exp_min, "experience_max": exp_max,
                    "job_type": "remote", "url": url, "posted_at": ""})
                print(f"  [WWR] {title} @ {company}")
        except Exception as e:
            print(f"WWR error: {e}")

# ── Greenhouse ────────────────────────────────────────────────────────────────

def crawl_greenhouse():
    print("Crawling Greenhouse job boards...")
    for company in GREENHOUSE_COMPANIES:
        try:
            data = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true",
                timeout=10).json()
            for j in data.get("jobs", []):
                title = j.get("title", "")
                if not is_target_role(title): continue
                text = BeautifulSoup(j.get("content", ""), "html.parser").get_text()
                exp_min, exp_max = extract_experience(text)
                location = j.get("location", {}).get("name", "Unknown")
                save_job({"title": title, "company": company.capitalize(),
                    "location": location, "experience_min": exp_min, "experience_max": exp_max,
                    "job_type": extract_job_type(location + " " + text[:500]),
                    "url": j.get("absolute_url", ""), "posted_at": j.get("updated_at", "")})
                print(f"  [Greenhouse/{company}] {title}")
            time.sleep(0.3)
        except Exception as e:
            print(f"Greenhouse error ({company}): {e}")

# ── Lever ─────────────────────────────────────────────────────────────────────

def crawl_lever():
    print("Crawling Lever job boards...")
    for company in LEVER_COMPANIES:
        try:
            data = requests.get(f"https://api.lever.co/v0/postings/{company}?mode=json", timeout=10).json()
            if not isinstance(data, list): continue
            for j in data:
                if not isinstance(j, dict): continue
                title = j.get("text", "")
                if not is_target_role(title): continue
                text = j.get("descriptionPlain", "") or ""
                exp_min, exp_max = extract_experience(text)
                location = j.get("categories", {}).get("location", "Unknown")
                commitment = j.get("categories", {}).get("commitment", "")
                save_job({"title": title, "company": company.capitalize(),
                    "location": location, "experience_min": exp_min, "experience_max": exp_max,
                    "job_type": extract_job_type(location + " " + commitment),
                    "url": j.get("hostedUrl", ""), "posted_at": ""})
                print(f"  [Lever/{company}] {title}")
            time.sleep(0.3)
        except Exception as e:
            print(f"Lever error ({company}): {e}")


# ── Jobicy API (free, no key) ─────────────────────────────────────────────────

def crawl_jobicy():
    print("Crawling Jobicy...")
    try:
        data = requests.get("https://jobicy.com/api/v2/remote-jobs?count=50&tag=devops", timeout=15).json()
        for j in data.get("jobs", []):
            title = j.get("jobTitle", "")
            if not is_target_role(title): continue
            text = BeautifulSoup(j.get("jobDescription", ""), "html.parser").get_text()
            exp_min, exp_max = extract_experience(text)
            save_job({"title": title, "company": j.get("companyName", ""),
                "location": j.get("jobGeo", "Remote"),
                "experience_min": exp_min, "experience_max": exp_max,
                "job_type": "remote", "url": j.get("url", ""), "posted_at": j.get("pubDate", "")})
            print(f"  [Jobicy] {title}")
    except Exception as e:
        print(f"Jobicy error: {e}")

# ── Himalayas API (free, no key) ──────────────────────────────────────────────

def crawl_himalayas():
    print("Crawling Himalayas...")
    for role in ["devops", "sre", "platform-engineer"]:
        try:
            data = requests.get(f"https://himalayas.app/jobs/api?q={role}&limit=50", timeout=15).json()
            for j in data.get("jobs", []):
                title = j.get("title", "")
                if not is_target_role(title): continue
                text = j.get("description", "")
                exp_min, exp_max = extract_experience(text)
                save_job({"title": title, "company": j.get("company", {}).get("name", ""),
                    "location": j.get("locationRestrictions", ["Remote"])[0] if j.get("locationRestrictions") else "Remote",
                    "experience_min": exp_min, "experience_max": exp_max,
                    "job_type": "remote", "url": j.get("applicationLink", ""), "posted_at": j.get("createdAt", "")})
                print(f"  [Himalayas] {title}")
        except Exception as e:
            print(f"Himalayas error: {e}")

# ── Wellfound (AngelList) public feed ─────────────────────────────────────────

def crawl_wellfound():
    print("Crawling Wellfound...")
    for role in ["devops-engineer", "site-reliability-engineer", "platform-engineer"]:
        try:
            resp = requests.get(f"https://wellfound.com/role/r/{role}", headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for card in soup.select("div[data-test='StartupResult']"):
                title_el = card.select_one("a[data-test='job-title']") or card.select_one("h2")
                if not title_el: continue
                title = title_el.get_text(strip=True)
                if not is_target_role(title): continue
                url = "https://wellfound.com" + title_el.get("href","") if title_el.get("href","").startswith("/") else title_el.get("href","")
                co_el = card.select_one("a[data-test='startup-link']") or card.select_one("h3")
                company = co_el.get_text(strip=True) if co_el else "Unknown"
                text = card.get_text()
                exp_min, exp_max = extract_experience(text)
                save_job({"title": title, "company": company, "location": "Unknown",
                    "experience_min": exp_min, "experience_max": exp_max,
                    "job_type": extract_job_type(text), "url": url, "posted_at": ""})
                print(f"  [Wellfound] {title}")
        except Exception as e:
            print(f"Wellfound error: {e}")

def scrape_job_page(url: str, company: str):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        title_el = soup.find(["h1", "h2"])
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or not is_target_role(title): return
        text = soup.get_text()
        exp_min, exp_max = extract_experience(text)
        save_job({"title": title, "company": company,
            "location": "Unknown", "experience_min": exp_min, "experience_max": exp_max,
            "job_type": extract_job_type(text[:1000]),
            "url": url, "posted_at": ""})
        print(f"  [Google] {title} @ {company}")
    except Exception:
        pass

def crawl_google():
    if not SERPAPI_KEY:
        print("Skipping Google search — SERPAPI_KEY not set.")
        return

    print("Crawling via Google (SerpApi)...")
    queries = [
        "site reliability engineer job opening 2025",
        "devops engineer job opening hiring now",
        "SRE engineer job posting apply",
        "platform engineer job opening remote",
    ]
    # Job board domains to skip (they're listing pages, not individual jobs)
    SKIP_DOMAINS = ["linkedin.com", "indeed.com", "glassdoor.com", "google.com",
                    "ziprecruiter.com", "monster.com", "dice.com", "builtin.com"]

    for query in queries:
        try:
            resp = requests.get("https://serpapi.com/search", params={
                "q": query,
                "api_key": SERPAPI_KEY,
                "engine": "google",
                "num": 10,
            }, timeout=15).json()

            for result in resp.get("organic_results", []):
                url = result.get("link", "")
                title = result.get("title", "")
                if any(d in url for d in SKIP_DOMAINS): continue
                if not is_target_role(title): continue
                company = result.get("displayed_link", "").split("//")[-1].split("/")[0].replace("www.", "")
                scrape_job_page(url, company)
                time.sleep(0.5)
        except Exception as e:
            print(f"Google search error: {e}")

# ── main ──────────────────────────────────────────────────────────────────────

def run_crawl():
    sources = os.environ.get("CRAWL_SOURCES", "all").lower().split(",")
    run_all = "all" in sources
    print("=== Starting crawl ===")
    if run_all or "remotive"   in sources: crawl_remotive()
    if run_all or "arbeitnow"  in sources: crawl_arbeitnow()
    if run_all or "wwr"        in sources: crawl_weworkremotely()
    if run_all or "jobicy"     in sources: crawl_jobicy()
    if run_all or "himalayas"  in sources: crawl_himalayas()
    if run_all or "wellfound"  in sources: crawl_wellfound()
    if run_all or "greenhouse" in sources: crawl_greenhouse()
    if run_all or "lever"      in sources: crawl_lever()
    if run_all or "google"     in sources: crawl_google()
    print("=== Crawl complete ===")

if __name__ == "__main__":
    run_crawl()
