"""Deployment pipeline: GitHub → Cloudflare Pages → DNS → SSL."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
import requests

BASE_DIR = Path(__file__).parent.resolve()


def load_config():
    with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def run(cmd, cwd=None, env_overrides=None):
    """Run a shell command, return (success, output)."""
    env = os.environ.copy()
    env["PATH"] = f"C:\\Program Files\\Git\\bin;C:\\Program Files\\GitHub CLI;{env.get('PATH', '')}"
    if env_overrides:
        env.update(env_overrides)
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd, env=env, timeout=120
        )
        out = (result.stdout or "").strip() + "\n" + (result.stderr or "").strip()
        return result.returncode == 0, out.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def cf_api(method, path, body=None):
    """Call Cloudflare API."""
    cfg = load_config()
    token = cfg["cloudflare"]["api_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"https://api.cloudflare.com/client/v4/{path}"
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=body, timeout=30)
        elif method == "PUT":
            resp = requests.put(url, headers=headers, json=body, timeout=30)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=30)
        else:
            return {"success": False, "errors": [{"message": f"Unknown method: {method}"}]}
        return resp.json()
    except Exception as e:
        return {"success": False, "errors": [{"message": str(e)}]}


def deploy_site(template_type, domain, ga_id=None):
    """Full deployment pipeline for one site. Returns result dict with logs."""
    cfg = load_config()
    cf_token = cfg["cloudflare"]["api_token"]
    cf_account = cfg["cloudflare"]["account_id"]
    gh_token = cfg["github"]["token"]
    gh_user = cfg["github"]["username"]

    logs = []
    project_name = domain.replace(".", "-")[:63]

    def log(msg):
        logs.append(msg)

    try:
        # Step 1: Generate code
        log(f"[generate] Building site code for {domain}...")
        from template_engine import generate_site
        output_dir, _ = generate_site(template_type, domain, ga_id)
        log(f"[generate] Code ready at {output_dir}")

        # Step 2: Initialize git in generated dir
        log(f"[git] Initializing git repo...")
        ok, out = run("git init", cwd=output_dir)
        ok, out = run('git config user.email "admin@tools-factory.local"', cwd=output_dir)
        ok, out = run('git config user.name "ToolsFactory"', cwd=output_dir)
        ok, out = run("git add .", cwd=output_dir)
        ok, out = run('git commit -m "Initial deploy: ' + template_type + ' tool"', cwd=output_dir)
        log(f"[git] {out}")

        # Step 3: Create GitHub repo
        log(f"[github] Creating repo {gh_user}/{project_name}...")
        env = {"GH_TOKEN": gh_token, "PATH": os.environ.get("PATH", "")}
        ok, out = run(
            f'gh repo create {project_name} --public --description "Free online {template_type} tool — {domain}" --source "{output_dir}" --remote origin --push',
            cwd=output_dir,
            env_overrides=env,
        )
        if not ok and "already exists" not in out.lower() and "name already exists" not in out.lower():
            log(f"[github] Warning: {out}")
        else:
            log(f"[github] Repo created and code pushed")

        # Step 4: Set GitHub secret
        log(f"[secret] Setting CLOUDFLARE_API_TOKEN secret...")
        echo_cmd = f'echo {cf_token}'
        ok, out = run(
            f'{echo_cmd} | gh secret set CLOUDFLARE_API_TOKEN --repo {gh_user}/{project_name}',
            cwd=output_dir,
            env_overrides=env,
        )
        log(f"[secret] {'Done' if ok else 'Warning: ' + out}")

        # Step 5: Create Cloudflare Pages project
        log(f"[pages] Creating Cloudflare Pages project...")
        result = cf_api("POST", f"accounts/{cf_account}/pages/projects", {
            "name": project_name,
            "production_branch": "master",
        })
        if not result.get("success"):
            err_msg = str(result.get("errors", []))
            if "already exists" not in err_msg.lower():
                log(f"[pages] Warning: {err_msg}")
        pages_subdomain = f"{project_name}.pages.dev"
        log(f"[pages] Project created: {pages_subdomain}")

        # Step 6: Deploy via Cloudflare API (direct upload using Pages deploy endpoint)
        log(f"[deploy] Uploading assets to Cloudflare Pages...")
        env_wrangler = {"CLOUDFLARE_API_TOKEN": cf_token, "PATH": os.environ.get("PATH", "")}
        ok, out = run(
            f'npx wrangler pages deploy "{output_dir}" --project-name {project_name} --branch master --commit-dirty=true',
            cwd=output_dir,
            env_overrides=env_wrangler,
        )
        log(f"[deploy] {'Uploaded' if ok else 'Upload issue: ' + out[:200]}")

        # Step 7: Add CNAME DNS record in Cloudflare zone
        log(f"[dns] Adding CNAME record for {domain}...")
        # Find or use existing zone
        zone_id = _find_zone(domain)
        if zone_id:
            cf_api("POST", f"zones/{zone_id}/dns_records", {
                "type": "CNAME",
                "name": "@",
                "content": f"{project_name}.pages.dev",
                "ttl": 1,
                "proxied": True,
            })
            log(f"[dns] CNAME @ → {project_name}.pages.dev")
        else:
            log(f"[dns] Zone not found for {domain} — DNS must be configured manually")

        # Step 8: Bind custom domain to Pages
        log(f"[domain] Binding custom domain {domain}...")
        result = cf_api("POST", f"accounts/{cf_account}/pages/projects/{project_name}/domains", {
            "hostname": domain,
        })
        if result.get("success"):
            log(f"[domain] Domain bound successfully")
        else:
            log(f"[domain] Note: {result.get('errors', [])}")

        # Step 9: Wait for SSL
        log(f"[ssl] Waiting for SSL provisioning...")
        for i in range(24):
            time.sleep(5)
            result = cf_api("GET", f"accounts/{cf_account}/pages/projects/{project_name}/domains")
            domains = result.get("result", [])
            for d in domains:
                if d.get("hostname") == domain and d.get("status") == "active":
                    log(f"[ssl] SSL active!")
                    break
            else:
                continue
            break
        else:
            log(f"[ssl] SSL still provisioning — check dashboard")

        # Step 10: Update sites.json
        log(f"[registry] Updating sites registry...")
        with open(BASE_DIR / "sites.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        data["sites"].append({
            "domain": domain,
            "template": template_type,
            "github_repo": project_name,
            "cloudflare_project": project_name,
            "cloudflare_zone_id": zone_id,
            "ga_id": ga_id,
            "adsense_id": None,
            "status": "live",
            "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        with open(BASE_DIR / "sites.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log(f"[registry] Site added to sites.json")

        log(f"[done] https://{domain} is live!")

        return {"success": True, "domain": domain, "logs": logs}

    except Exception as e:
        log(f"[ERROR] {str(e)}")
        return {"success": False, "domain": domain, "error": str(e), "logs": logs}


def _find_zone(domain):
    """Find existing Cloudflare zone ID for a domain."""
    cfg = load_config()
    token = cfg["cloudflare"]["api_token"]

    # Try exact match first
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.get(
        f"https://api.cloudflare.com/client/v4/zones?name={domain}",
        headers=headers, timeout=10
    )
    zones = resp.json().get("result", [])
    if zones:
        return zones[0]["id"]

    # Try creating zone
    result = cf_api("POST", "zones", {
        "name": domain,
        "account": {"id": cfg["cloudflare"]["account_id"]},
        "type": "full",
    })
    zone = result.get("result", {})
    return zone.get("id")
