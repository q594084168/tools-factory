"""Template engine — replaces placeholders in tool site templates."""

import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
TEMPLATES_DIR = BASE_DIR / "templates"
GENERATED_DIR = BASE_DIR / "generated"

PLACEHOLDER_MAP = {
    "DOMAIN": "domain",
    "SITE_NAME": "site_name",
    "TOOL_TITLE": "tool_title",
    "TOOL_DESCRIPTION": "tool_description",
    "GA_ID": "ga_id",
    "ADSENSE_ID": "adsense_id",
    "CANONICAL_URL": "canonical_url",
}


def generate_site(template_type, domain, ga_id=None, adsense_id=None):
    """Generate site files from template, replacing all placeholders."""
    template_dir = TEMPLATES_DIR / template_type
    if not template_dir.exists():
        raise ValueError(f"Template not found: {template_type}")

    # Load template metadata
    meta_path = template_dir / "meta.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    else:
        meta = {}

    # Compute replacements
    site_name = domain.split(".")[0].capitalize()
    ga_script = ""
    if ga_id:
        ga_script = f'<script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","{ga_id}");</script>'

    replacements = {
        "domain": domain,
        "site_name": site_name,
        "tool_title": meta.get("tool_title", site_name),
        "tool_description": meta.get("tool_description", f"Free online {template_type} tool."),
        "ga_id": ga_script,
        "adsense_id": adsense_id or "",
        "canonical_url": f"https://{domain}/",
    }

    # Generate output directory
    output_dir = GENERATED_DIR / domain
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Copy and process template.html
    template_html = template_dir / "template.html"
    with open(template_html, "r", encoding="utf-8") as f:
        content = f.read()

    for placeholder, key in PLACEHOLDER_MAP.items():
        content = content.replace("{{" + placeholder + "}}", replacements[key])

    with open(output_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(content)

    # Copy README if exists
    readme_src = template_dir / "README.md"
    if readme_src.exists():
        shutil.copy(readme_src, output_dir / "README.md")

    # Copy .github directory if exists
    github_src = template_dir / ".github"
    if github_src.exists():
        shutil.copytree(github_src, output_dir / ".github", dirs_exist_ok=True)

    # Generate sitemap.xml
    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://{domain}/</loc>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>'''
    with open(output_dir / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap)

    return str(output_dir), replacements


def list_templates():
    """Return list of available template types with metadata."""
    templates = []
    if not TEMPLATES_DIR.exists():
        return templates
    for d in sorted(TEMPLATES_DIR.iterdir()):
        if d.is_dir():
            meta_path = d / "meta.json"
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            else:
                meta = {}
            templates.append({
                "id": d.name,
                "name": meta.get("name", d.name),
                "tool_title": meta.get("tool_title", d.name),
                "tool_description": meta.get("tool_description", ""),
            })
    return templates
