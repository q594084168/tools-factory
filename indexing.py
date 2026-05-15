"""Google Indexing API — submits new URLs for faster crawling."""
import json
import os
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
LOG_PATH = DATA_DIR / "indexing_log.json"

PROXY_URL = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")


def _load_log():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOG_PATH.exists():
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_log(log):
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def submit_url(url, credentials_json_path=None):
    """Submit a single URL to Google Indexing API.

    Requires a Google Cloud service account JSON key file.
    Returns: {'success': bool, 'status_code': int, 'body': dict}
    """
    return _batch_submit([url], credentials_json_path)


def submit_batch(urls, credentials_json_path=None, delay=1.0):
    """Submit multiple URLs with rate limiting (200/day free quota).

    Returns: {'submitted': int, 'failed': int, 'results': list}
    """
    return _batch_submit(urls, credentials_json_path, delay)


def _batch_submit(urls, credentials_json_path=None, delay=1.0):
    if credentials_json_path is None:
        creds_path = BASE_DIR / "gcp-service-account.json"
    else:
        creds_path = Path(credentials_json_path)

    if not creds_path.exists():
        return {"success": False, "error": f"Credentials file not found: {creds_path}", "results": []}

    # Set up proxy-aware session
    session = requests.Session()
    if PROXY_URL:
        session.proxies = {"http": PROXY_URL, "https": PROXY_URL}

    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        credentials = service_account.Credentials.from_service_account_file(
            str(creds_path),
            scopes=["https://www.googleapis.com/auth/indexing"],
        )
        credentials.refresh(Request(session=session))
        token = credentials.token
    except ImportError:
        return {"success": False, "error": "Missing google-auth / google-auth-oauthlib. Run: pip install google-auth google-auth-oauthlib requests", "results": []}
    except Exception as e:
        return {"success": False, "error": f"Auth failed: {e}", "results": []}

    log = _load_log()
    results = []
    submitted = 0
    failed = 0

    for url in urls:
        if log.get(url) and log[url].get("status") == "ok":
            results.append({"url": url, "already_submitted": True})
            continue

        try:
            resp = session.post(
                "https://indexing.googleapis.com/v3/urlNotifications:publish",
                json={"url": url, "type": "URL_UPDATED"},
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=30,
            )
            data = resp.json() if resp.text else {}
            ok = resp.status_code == 200

            log[url] = {"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "status": "ok" if ok else "fail", "response": data}
            results.append({"url": url, "success": ok, "status_code": resp.status_code, "body": data})

            if ok:
                submitted += 1
            else:
                failed += 1

            time.sleep(delay)
        except requests.exceptions.RequestException as e:
            results.append({"url": url, "error": str(e)})
            failed += 1

    _save_log(log)
    return {"submitted": submitted, "failed": failed, "results": results}


def get_status():
    """Return summary: how many URLs submitted in last 7 days."""
    log = _load_log()
    total = len(log)
    recent = 0
    now = time.time()
    for entry in log.values():
        try:
            t = time.mktime(time.strptime(entry.get("time", ""), "%Y-%m-%dT%H:%M:%SZ"))
            if now - t < 7 * 86400:
                recent += 1
        except (ValueError, OSError):
            pass
    return {"total_submitted": total, "last_7_days": recent, "daily_quota": 200}
