"""Monitoring: Cloudflare Analytics integration, RPM estimation, weekly reports."""

import json
from pathlib import Path
from datetime import datetime
import requests

BASE_DIR = Path(__file__).parent.resolve()

RPM_ESTIMATES = {
    "image-compress": {"low": 8, "mid": 12, "high": 15},
    "json-formatter": {"low": 10, "mid": 15, "high": 20},
    "qr-generator": {"low": 6, "mid": 10, "high": 14},
    "password-generator": {"low": 5, "mid": 8, "high": 12},
    "word-counter": {"low": 5, "mid": 8, "high": 10},
}


def load_config():
    with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_sites():
    with open(BASE_DIR / "sites.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_cloudflare_zone_stats():
    """Fetch zone status from Cloudflare API for all zones under the account."""
    cfg = load_config()
    token = cfg["cloudflare"]["api_token"]
    account_id = cfg["cloudflare"]["account_id"]

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.get(
        f"https://api.cloudflare.com/client/v4/zones?account.id={account_id}",
        headers=headers, timeout=10
    )
    result = resp.json()
    zones = result.get("result", [])

    zone_stats = {}
    for zone in zones:
        zone_stats[zone["name"]] = {
            "zone_id": zone["id"],
            "status": zone.get("status", "unknown"),
            "name_servers": zone.get("name_servers", []),
            "paused": zone.get("paused", False),
        }
    return zone_stats


def get_estimated_revenue(uv_count, template_type):
    """Estimate revenue from daily UV count and template type RPM."""
    rpm = RPM_ESTIMATES.get(template_type, {"low": 5, "mid": 8, "high": 12})
    rpm_mid = rpm["mid"]
    daily_revenue = (uv_count / 1000) * rpm_mid
    monthly_revenue = daily_revenue * 30
    return {
        "rpm_estimate": rpm_mid,
        "rpm_low": rpm["low"],
        "rpm_high": rpm["high"],
        "daily_revenue": round(daily_revenue, 2),
        "monthly_revenue": round(monthly_revenue, 2),
    }


def get_weekly_report():
    """Generate a weekly traffic report markdown for all sites."""
    data = load_sites()
    sites = data.get("sites", [])

    lines = [
        "# Weekly Traffic Report",
        f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        f"Total Sites: {len(sites)}\n",
    ]

    # Get live Cloudflare stats
    try:
        zone_stats = get_cloudflare_zone_stats()
    except Exception:
        zone_stats = {}

    for site in sites:
        domain = site["domain"]
        lines.append(f"## {domain}")
        lines.append(f"- Template: {site.get('template', 'unknown')}")
        lines.append(f"- Status: {site.get('status', 'unknown')}")
        lines.append(f"- Deployed: {site.get('deployed_at', 'unknown')}")
        lines.append(f"- Last Updated: {site.get('last_updated', 'unknown')}")

        cf_stat = zone_stats.get(domain, {})
        if cf_stat:
            lines.append(f"- Cloudflare Status: {cf_stat.get('status', 'unknown')}")
        lines.append("")

    report = "\n".join(lines)

    # Save to reports folder
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"report-{datetime.now().strftime('%Y%m%d')}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return report, str(report_path)
