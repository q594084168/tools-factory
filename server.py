"""
Tools Factory — Local backend server.
Double-click start.bat to launch.
"""

import json
import os
import time
import threading
import webbrowser
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory, Response

app = Flask(__name__, static_folder=".", static_url_path="")

BASE_DIR = Path(__file__).parent.resolve()


def load_config():
    with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_sites():
    with open(BASE_DIR / "sites.json", "r", encoding="utf-8") as f:
        return json.load(f)


def save_sites(data):
    with open(BASE_DIR / "sites.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# --- Static files ---

@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "panel.html")


@app.route("/api/status")
def api_status():
    return jsonify({"ok": True, "version": "1.0.0", "time": datetime.now().isoformat()})


# --- Templates ---

@app.route("/api/templates")
def api_list_templates():
    from template_engine import list_templates
    return jsonify({"templates": list_templates()})


# --- Domain Generation ---

@app.route("/api/domains/generate")
def api_generate_domains():
    from domain_generator import generate_domains
    template_type = request.args.get("template", "image-compress")
    count = int(request.args.get("count", 10))
    domains = generate_domains(template_type, count)
    return jsonify({"domains": domains})


# --- Code Generation (without deploy) ---

@app.route("/api/generate", methods=["POST"])
def api_generate():
    from template_engine import generate_site
    data = request.json
    template_type = data["template"]
    domain = data["domain"]
    ga_id = data.get("ga_id")
    adsense_id = data.get("adsense_id")
    output_dir, replacements = generate_site(template_type, domain, ga_id, adsense_id)
    return jsonify({"success": True, "output_dir": output_dir, "replacements": replacements})


# --- Deploy ---

@app.route("/api/deploy", methods=["POST"])
def api_deploy():
    from deployer import deploy_site
    data = request.json
    domains = data.get("domains", [])
    template_type = data.get("template")
    ga_id = data.get("ga_id")

    if not domains or not template_type:
        return jsonify({"success": False, "error": "Missing domains or template"}), 400

    results = []
    for domain in domains:
        try:
            result = deploy_site(template_type, domain, ga_id)
            results.append(result)
        except Exception as e:
            results.append({"success": False, "domain": domain, "error": str(e)})

    return jsonify({"success": True, "results": results})


# --- Deploy Stream (SSE for real-time progress) ---

@app.route("/api/deploy/stream", methods=["POST"])
def api_deploy_stream():
    from deployer import deploy_site
    data = request.json
    domains = data.get("domains", [])
    template_type = data.get("template")
    ga_id = data.get("ga_id")

    def generate():
        for domain in domains:
            yield f"data: {json.dumps({'type': 'start', 'domain': domain})}\n\n"
            try:
                result = deploy_site(template_type, domain, ga_id)
                yield f"data: {json.dumps({'type': 'result', 'domain': domain, 'success': result.get('success', False), 'logs': result.get('logs', [])})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'domain': domain, 'error': str(e)})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


# --- Sites Management ---

@app.route("/api/sites")
def api_list_sites():
    data = load_sites()
    sites = data.get("sites", [])

    # Enrich with Cloudflare status
    try:
        cfg = load_config()
        token = cfg["cloudflare"]["api_token"]
        account_id = cfg["cloudflare"]["account_id"]
        import requests
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        for site in sites:
            project = site.get("cloudflare_project", "")
            try:
                resp = requests.get(
                    f"https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects/{project}/domains",
                    headers=headers, timeout=10
                )
                result = resp.json()
                domains = result.get("result", [])
                for d in domains:
                    if d.get("hostname") == site["domain"]:
                        site["ssl_status"] = d.get("status", "unknown")
                        break
                else:
                    site["ssl_status"] = "not_found"
            except Exception:
                site["ssl_status"] = "error"
    except Exception:
        for site in sites:
            site["ssl_status"] = "unknown"

    return jsonify({"sites": sites})


@app.route("/api/sites/<domain>", methods=["DELETE"])
def api_delete_site(domain):
    data = load_sites()
    data["sites"] = [s for s in data["sites"] if s["domain"] != domain]
    save_sites(data)
    return jsonify({"success": True})


# --- Monitoring ---

@app.route("/api/monitoring")
def api_monitoring():
    from monitor import get_estimated_revenue, RPM_ESTIMATES
    data = load_sites()
    sites = data.get("sites", [])

    enriched = []
    total_uv = 0
    for site in sites:
        template_type = site.get("template", "image-compress")
        uv = site.get("last_uv", 0)
        revenue = get_estimated_revenue(uv, template_type)
        enriched.append({
            **site,
            "uv_7d": uv,
            "rpm_estimate": revenue["rpm_estimate"],
            "rpm_low": revenue["rpm_low"],
            "rpm_high": revenue["rpm_high"],
            "daily_revenue": revenue["daily_revenue"],
            "monthly_revenue": revenue["monthly_revenue"],
        })
        total_uv += uv

    return jsonify({
        "sites": enriched,
        "total_uv_7d": total_uv,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "rpm_reference": RPM_ESTIMATES,
    })


@app.route("/api/report")
def api_report():
    from monitor import get_weekly_report
    report, path = get_weekly_report()
    return jsonify({"report": report, "saved_to": path})


# --- Launch ---

if __name__ == "__main__":
    cfg = load_config()
    port = cfg["preferences"]["port"]
    if cfg["preferences"].get("auto_open_browser", True):
        threading.Timer(0.8, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    print(f"\n  Tools Factory running at http://localhost:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
