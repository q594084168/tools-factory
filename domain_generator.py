"""Domain name generation and availability checking."""

import json
import time
from pathlib import Path
import requests

BASE_DIR = Path(__file__).parent.resolve()

TLD_SCORES = {".com": 1.0, ".net": 0.75, ".org": 0.5, ".io": 0.4, ".co": 0.35}


def load_keywords(template_type):
    """Load keyword matrix for a template type."""
    path = BASE_DIR / "templates" / template_type / "keywords.json"
    if not path.exists():
        return {"primary": ["tool"], "suffixes": ["online", "free", "now"], "tlds": [".com", ".net"]}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_domains(template_type, count=10):
    """Generate domain candidates and check availability via RDAP."""
    kw = load_keywords(template_type)
    candidates = []

    primaries = kw.get("primary", [])
    suffixes = kw.get("suffixes", [])
    tlds = kw.get("tlds", [".com", ".net"])

    # Generate combinations
    for primary in primaries:
        for suffix in suffixes:
            candidates.append(f"{primary}{suffix}")
            candidates.append(f"{suffix}{primary}")
        candidates.append(primary)

    # Score each candidate with each TLD
    scored = []
    seen = set()
    for name in candidates:
        for tld in tlds:
            domain = f"{name}{tld}"
            if domain in seen:
                continue
            seen.add(domain)
            tld_score = TLD_SCORES.get(tld, 0.3)
            exact_bonus = 1.0 if name == candidates[0] else 0.7
            score = int(tld_score * exact_bonus * 100)
            scored.append({"domain": domain, "score": score, "tld": tld, "name": name})

    scored.sort(key=lambda x: x["score"], reverse=True)

    # Check availability via RDAP (first 30 candidates)
    available = []
    for item in scored[:30]:
        if len(available) >= count:
            break
        time.sleep(0.3)
        is_avail = check_available(item["domain"])
        if is_avail:
            available.append({**item, "available": True})
        else:
            available.append({**item, "available": False, "score": 0})

    # Sort: available first by score, then unavailable
    available.sort(key=lambda x: (x.get("available", False), x["score"]), reverse=True)
    return available[:count]


def check_available(domain):
    """Check domain availability via RDAP. Returns True if likely available."""
    tld = domain[domain.rfind("."):]
    try:
        resp = requests.get(
            f"https://rdap.verisign.com/{tld.lstrip('.')}/v1/domain/{domain}",
            timeout=5
        )
        if resp.status_code == 404:
            return True
        if resp.status_code == 200:
            return False
        return True
    except Exception:
        import socket
        try:
            socket.gethostbyname(domain)
            return False
        except socket.gaierror:
            return True
