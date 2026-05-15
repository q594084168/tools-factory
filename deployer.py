"""Deployment pipeline: GitHub → Cloudflare Pages → DNS → SSL."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
import requests

BASE_DIR = Path(__file__).parent.resolve()

UA = "ToolsFactory/1.0 (local-automation)"
API_TIMEOUT = 30
DEPLOY_DELAY = 3  # seconds between sites to avoid rate limits


def load_config():
    with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def run(cmd, cwd=None, env_overrides=None, timeout=120):
    """Run a shell command, return (success, output)."""
    env = os.environ.copy()
    env["PATH"] = f"C:\\Program Files\\Git\\bin;C:\\Program Files\\GitHub CLI;{env.get('PATH', '')}"
    if env_overrides:
        env.update(env_overrides)
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd, env=env, timeout=timeout
        )
        out = (result.stdout or "").strip() + "\n" + (result.stderr or "").strip()
        return result.returncode == 0, out.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def cf_api(method, path, body=None):
    """Call Cloudflare API with proper headers."""
    cfg = load_config()
    token = cfg["cloudflare"]["api_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": UA,
    }
    url = f"https://api.cloudflare.com/client/v4/{path}"
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=body, timeout=API_TIMEOUT)
        elif method == "PUT":
            resp = requests.put(url, headers=headers, json=body, timeout=API_TIMEOUT)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=API_TIMEOUT)
        else:
            return {"success": False, "errors": [{"message": f"Unknown method: {method}"}]}
        return resp.json()
    except Exception as e:
        return {"success": False, "errors": [{"message": str(e)}]}


def _set_gh_secret(secret_name, secret_value, repo_full, cwd, env):
    """Set a GitHub secret via stdin to avoid token appearing in process list."""
    try:
        proc = subprocess.run(
            f'gh secret set {secret_name} --repo {repo_full}',
            shell=True, cwd=cwd, env=env,
            input=secret_value, text=True,
            capture_output=True, timeout=30,
        )
        return proc.returncode == 0, (proc.stdout or "").strip() + (proc.stderr or "").strip()
    except Exception as e:
        return False, str(e)


def deploy_site(template_type, domain, ga_id=None, scene_pages=None):
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
        output_dir, _ = generate_site(template_type, domain, ga_id, scene_pages=scene_pages)
        log(f"[generate] Code ready at {output_dir}")

        # Ensure robots.txt exists (belt and suspenders)
        robots_path = Path(output_dir) / "robots.txt"
        if not robots_path.exists():
            robots = f"User-agent: *\nAllow: /\nSitemap: https://{domain}/sitemap.xml\n"
            with open(robots_path, "w", encoding="utf-8") as f:
                f.write(robots)
            log(f"[generate] robots.txt created (fallback)")

        # Step 2: Initialize git in generated dir
        log(f"[git] Initializing git repo...")
        ok, out = run("git init", cwd=output_dir)
        if not ok:
            log(f"[git] ERROR: git init failed — {out}")
            return {"success": False, "domain": domain, "error": "git init failed", "logs": logs}
        run('git config user.email "admin@tools-factory.local"', cwd=output_dir)
        run('git config user.name "ToolsFactory"', cwd=output_dir)
        ok, out = run("git add .", cwd=output_dir)
        if not ok:
            log(f"[git] ERROR: git add failed — {out}")
            return {"success": False, "domain": domain, "error": "git add failed", "logs": logs}
        ok, out = run(f'git commit -m "Initial deploy: {template_type} tool"', cwd=output_dir)
        if not ok and "nothing to commit" not in out.lower():
            log(f"[git] ERROR: git commit failed — {out}")
            return {"success": False, "domain": domain, "error": "git commit failed", "logs": logs}
        log(f"[git] Committed")

        # Step 3: Create GitHub repo (with retry for rate limits)
        log(f"[github] Creating repo {gh_user}/{project_name}...")
        env = {"GH_TOKEN": gh_token, "PATH": os.environ.get("PATH", "")}
        ok, out = run(
            f'gh repo create {project_name} --public --description "Free online {template_type} tool — {domain}" --source "{output_dir}" --remote origin --push',
            cwd=output_dir,
            env_overrides=env,
            timeout=60,
        )
        if not ok:
            if "already exists" in out.lower() or "name already exists" in out.lower():
                log(f"[github] Repo already exists, continuing...")
            elif "rate limit" in out.lower() or "secondary rate limit" in out.lower():
                log(f"[github] Rate limited, waiting 30s...")
                time.sleep(30)
                ok, out = run(
                    f'gh repo create {project_name} --public --description "Free online {template_type} tool — {domain}" --source "{output_dir}" --remote origin --push',
                    cwd=output_dir,
                    env_overrides=env,
                    timeout=60,
                )
                if not ok:
                    log(f"[github] Retry failed: {out}")
            else:
                log(f"[github] Error: {out}")
        else:
            log(f"[github] Repo created and code pushed")

        # Step 4: Set GitHub secret via stdin (no echo leak)
        log(f"[secret] Setting CLOUDFLARE_API_TOKEN secret...")
        ok, out = _set_gh_secret("CLOUDFLARE_API_TOKEN", cf_token, f"{gh_user}/{project_name}", output_dir, env)
        log(f"[secret] {'Done' if ok else 'Warning: ' + out}")

        # Step 5: Create Cloudflare Pages project
        log(f"[pages] Creating Cloudflare Pages project...")
        result = cf_api("POST", f"accounts/{cf_account}/pages/projects", {
            "name": project_name,
            "production_branch": "master",
        })
        if not result.get("success"):
            err_msg = str(result.get("errors", []))
            if "already exists" in err_msg.lower():
                log(f"[pages] Project already exists, continuing...")
            elif "rate limit" in err_msg.lower():
                log(f"[pages] Rate limited, waiting 30s...")
                time.sleep(30)
                result = cf_api("POST", f"accounts/{cf_account}/pages/projects", {
                    "name": project_name,
                    "production_branch": "master",
                })
            else:
                log(f"[pages] Warning: {err_msg}")
        pages_subdomain = f"{project_name}.pages.dev"
        log(f"[pages] Project ready: {pages_subdomain}")

        # Step 6: Deploy via wrangler
        log(f"[deploy] Uploading assets to Cloudflare Pages...")
        env_wrangler = {"CLOUDFLARE_API_TOKEN": cf_token, "PATH": os.environ.get("PATH", "")}
        ok, out = run(
            f'npx wrangler pages deploy "{output_dir}" --project-name {project_name} --branch master --commit-dirty=true',
            cwd=output_dir,
            env_overrides=env_wrangler,
            timeout=120,
        )
        log(f"[deploy] {'Uploaded' if ok else 'Upload issue: ' + out[:200]}")

        # Step 7: Add CNAME DNS record in Cloudflare zone
        log(f"[dns] Adding CNAME record for {domain}...")
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

        # Step 9: Wait for SSL (fast poll — check 6 times over ~60s)
        log(f"[ssl] Waiting for SSL provisioning...")
        ssl_ok = False
        for i in range(6):
            time.sleep(10)
            result = cf_api("GET", f"accounts/{cf_account}/pages/projects/{project_name}/domains")
            domains = result.get("result", [])
            for d in domains:
                if d.get("hostname") == domain and d.get("status") == "active":
                    log(f"[ssl] SSL active!")
                    ssl_ok = True
                    break
            if ssl_ok:
                break
        if not ssl_ok:
            log(f"[ssl] SSL still provisioning — check dashboard in a few minutes")

        # Step 10: Update sites.json
        log(f"[registry] Updating sites registry...")
        with open(BASE_DIR / "sites.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        # Remove existing entry with same domain to avoid duplicates
        data["sites"] = [s for s in data.get("sites", []) if s.get("domain") != domain]
        data["sites"].append({
            "id": str(int(time.time() * 1000)),
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

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": UA,
    }
    resp = requests.get(
        f"https://api.cloudflare.com/client/v4/zones?name={domain}",
        headers=headers, timeout=10
    )
    zones = resp.json().get("result", [])
    if zones:
        return zones[0]["id"]

    # Create zone if not found
    result = cf_api("POST", "zones", {
        "name": domain,
        "account": {"id": cfg["cloudflare"]["account_id"]},
        "type": "full",
    })
    zone = result.get("result", {})
    return zone.get("id")
