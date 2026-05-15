"""Template engine — replaces placeholders in tool site templates."""

import html
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

_SCENE_BASE_CSS = """:root{--primary:#4F46E5;--primary-dark:#4338CA;--bg:#F8FAFC;--card-bg:#FFFFFF;--text:#1E293B;--text-secondary:#64748B;--border:#E2E8F0;--radius:12px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.container{max-width:960px;margin:0 auto;padding:0 24px}
header{background:#1E293B;color:#F1F5F9;padding:16px 0;box-shadow:0 2px 8px rgba(0,0,0,.15)}
header .container{display:flex;justify-content:space-between;align-items:center}
header nav{display:flex;gap:24px}header nav a{color:#94A3B8;text-decoration:none;font-size:.9rem;font-weight:500}header nav a:hover{color:#fff}
.subtitle{color:var(--text-secondary);max-width:560px;margin:0 auto}
.tool-area{max-width:700px;margin:0 auto 24px;padding:0 24px}
.tool-area textarea{width:100%;border:2px dashed var(--border);border-radius:var(--radius);padding:20px;font-family:'Consolas',monospace;font-size:14px;resize:vertical;background:var(--card-bg);min-height:200px}
.tool-area textarea:focus{outline:none;border-color:var(--primary);border-style:solid}
.btn-row{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:24px}
.btn{padding:12px 28px;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;font-family:inherit}.btn:active{transform:scale(.97)}
.btn-primary{background:var(--primary);color:#fff}.btn-primary:hover{background:var(--primary-dark)}
.btn-secondary{background:var(--card-bg);color:var(--text);border:1px solid var(--border)}
.output-area{margin-top:16px;background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);padding:20px;min-height:80px;word-break:break-all;display:none}
.error-msg{color:#DC2626;font-size:.85rem;margin-top:8px;display:none}
.ad-slot{background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);min-height:90px;display:flex;align-items:center;justify-content:center;max-width:728px;margin:0 auto 24px}
.ad-placeholder{color:var(--border);font-size:.8rem;text-transform:uppercase;letter-spacing:.1em}
.faq-section{padding:40px 0;text-align:left}.faq-section h2{font-size:1.5rem;margin-bottom:24px;text-align:center}
.faq-item{margin-bottom:20px}.faq-item h3{font-size:1rem;margin-bottom:6px;color:var(--primary)}
.faq-item p{color:var(--text-secondary);font-size:.9rem}
footer{background:#1E293B;color:#94A3B8;padding:32px 0;text-align:center;font-size:.85rem}
footer a{color:#CBD5E1;text-decoration:none}"""


def generate_site(template_type, domain, ga_id=None, adsense_id=None, scene_pages=None):
    """Generate site files from template, replacing all placeholders.

    If scene_pages is provided, also generates sub-directories for each scene.
    """
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

    # Copy and process main template.html → homepage
    template_html = template_dir / "template.html"
    if template_html.exists():
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

    # Generate scene sub-pages
    if scene_pages is None:
        scene_pages = []

    for scene in scene_pages:
        slug = scene["slug"]
        sub_dir = output_dir / slug
        sub_dir.mkdir(parents=True, exist_ok=True)
        html = _build_scene_page(scene, replacements, scene_pages)
        with open(sub_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(html)

    # Generate sitemap.xml
    sitemap = _build_sitemap(domain, scene_pages)
    with open(output_dir / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap)

    # Generate robots.txt
    robots = f"""User-agent: *
Allow: /
Sitemap: https://{domain}/sitemap.xml
"""
    with open(output_dir / "robots.txt", "w", encoding="utf-8") as f:
        f.write(robots)

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


def _build_sitemap(domain, scene_pages):
    """Build sitemap.xml listing homepage + all scene sub-pages."""
    urls = [f"  <url>\n    <loc>https://{domain}/</loc>\n    <changefreq>monthly</changefreq>\n    <priority>1.0</priority>\n  </url>"]
    for scene in scene_pages:
        urls.append(f"  <url>\n    <loc>https://{domain}/{scene['slug']}/</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"


def _build_scene_page(scene, replacements, all_scenes):
    """Build HTML for one scene-targeted sub-page with FAQ Schema and internal links."""
    site_name = html.escape(replacements["site_name"])
    ga_script = replacements["ga_id"]
    domain = replacements["domain"]

    # Escape all user-controllable data
    esc_title = html.escape(scene["title"])
    esc_desc = html.escape(scene["description"])
    esc_scenario = html.escape(scene["scenario"])
    esc_tool_desc = html.escape(replacements["tool_description"])

    faq_items = scene.get("faqs", [])
    faq_json = json.dumps([{
        "@type": "Question",
        "name": faq["q"],
        "acceptedAnswer": {"@type": "Answer", "text": faq["a"]}
    } for faq in faq_items]).replace('</', '<\\/')

    breadcrumb_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"https://{domain}/"},
            {"@type": "ListItem", "position": 2, "name": scene["scenario"], "item": f"https://{domain}/{scene['slug']}/"},
        ]
    }).replace('</', '<\\/')

    software_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": scene["title"],
        "url": f"https://{domain}/{scene['slug']}/",
        "description": scene["description"],
        "applicationCategory": "UtilityApplication",
        "operatingSystem": "All",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
    }).replace('</', '<\\/')

    siblings = [s for s in all_scenes if s["slug"] != scene["slug"]]
    related_links = ""
    for sib in siblings[:6]:
        related_links += f'                    <li><a href="/{sib["slug"]}/">{html.escape(sib["scenario"])}</a></li>\n'

    faq_html = ""
    for faq in faq_items:
        faq_html += f'                <div class="faq-item">\n                    <h3>{html.escape(faq["q"])}</h3>\n                    <p>{html.escape(faq["a"])}</p>\n                </div>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{esc_desc}">
    <meta name="robots" content="index, follow">
    <meta property="og:title" content="{esc_title}">
    <meta property="og:description" content="{esc_desc}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://{domain}/{scene['slug']}/">
    <link rel="canonical" href="https://{domain}/{scene['slug']}/">
    <title>{esc_title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    {ga_script}
    <style>
        {_SCENE_BASE_CSS}
        .scene-hero{{padding:40px 0 24px;text-align:center}}
        .scene-hero h1{{font-size:2rem;font-weight:800;margin-bottom:12px;line-height:1.3}}
        @media(max-width:640px){{.scene-hero h1{{font-size:1.5rem}}}}
        .scene-body{{max-width:700px;margin:0 auto;padding:0 24px 40px}}
        .scene-body h2{{font-size:1.25rem;margin:32px 0 12px;color:#1E293B}}
        .scene-body p{{color:#475569;margin-bottom:12px;font-size:1rem;line-height:1.7}}
        .related-tools{{background:#F8FAFC;border-top:1px solid #E2E8F0;padding:40px 0}}
        .related-tools .container{{max-width:960px;margin:0 auto;padding:0 24px}}
        .related-tools h2{{font-size:1.5rem;margin-bottom:20px;text-align:center}}
        .related-tools ul{{list-style:none;display:grid;grid-template-columns:repeat(2,1fr);gap:12px;max-width:600px;margin:0 auto}}
        @media(max-width:640px){{.related-tools ul{{grid-template-columns:1fr}}}}
        .related-tools a{{color:#4F46E5;text-decoration:none;font-weight:500;padding:10px 16px;display:block;background:#fff;border-radius:8px;border:1px solid #E2E8F0;transition:all .15s}}
        .related-tools a:hover{{border-color:#4F46E5;box-shadow:0 2px 8px rgba(79,70,229,0.12)}}
        .breadcrumb{{font-size:.85rem;color:#64748B;padding:16px 0;max-width:960px;margin:0 auto}}
        .breadcrumb a{{color:#4F46E5;text-decoration:none}}.breadcrumb a:hover{{text-decoration:underline}}
    </style>
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": {faq_json}
    }}
    </script>
    <script type="application/ld+json">
    {breadcrumb_json}
    </script>
    <script type="application/ld+json">
    {software_json}
    </script>
</head>
<body>
    <header>
        <div class="container">
            <a href="/" class="logo">{site_name}</a>
            <nav>
                <a href="/">Home</a>
                <a href="#faq">FAQ</a>
                <a href="#related">Related Tools</a>
            </nav>
        </div>
    </header>
    <main>
        <div class="breadcrumb"><a href="/">Home</a> / {esc_scenario}</div>
        <section class="scene-hero">
            <h1>{esc_title}</h1>
            <p class="subtitle">{esc_desc}</p>
        </section>
        <section class="tool-area">
            <textarea id="toolInput" placeholder="Paste or upload your content here..."></textarea>
            <div class="output-area" id="toolOutput"></div>
            <p class="error-msg" id="errorMsg"></p>
            <div class="btn-row">
                <button class="btn btn-primary" id="actionBtn">Process Now</button>
                <button class="btn btn-secondary" id="clearBtn">Clear</button>
                <button class="btn btn-secondary" id="copyBtn">Copy Result</button>
            </div>
            <div class="ad-slot"><div class="ad-placeholder">Advertisement</div></div>
        </section>
        <section class="scene-body">
            <h2>About {esc_scenario}</h2>
            <p>This tool helps you {esc_scenario.lower()}. {esc_tool_desc} No downloads or installations required — everything runs directly in your browser.</p>
            <h2>How to {esc_scenario}</h2>
            <p>Step 1: Upload or paste your content into the tool above.</p>
            <p>Step 2: Click "Process Now" and wait a few seconds.</p>
            <p>Step 3: Copy or download the result. Done.</p>
            <h2>Why Use This Tool?</h2>
            <p>Unlike desktop software, there is nothing to install. Unlike other online tools, we do not require signup. Unlike mobile apps, this works on any device with a browser. And unlike paid alternatives, it is completely free.</p>
        </section>
        <section class="faq-section" id="faq">
            <div class="container">
                <h2>Frequently Asked Questions</h2>
{faq_html}            </div>
        </section>
        <section class="related-tools" id="related">
            <div class="container">
                <h2>Related Tools</h2>
                <ul>
{related_links}                </ul>
            </div>
        </section>
    </main>
    <footer>
        <div class="container">
            <p>&copy; 2026 {site_name}. All rights reserved. | <a href="/">Home</a> | <a href="#faq">FAQ</a></p>
            <p style="margin-top:8px">All processing happens locally in your browser. Your data is never uploaded.</p>
        </div>
    </footer>
    <script>
        const input=document.getElementById('toolInput');const output=document.getElementById('toolOutput');const errorMsg=document.getElementById('errorMsg');
        document.getElementById('actionBtn').addEventListener('click',()=>{{const v=input.value.trim();if(!v){{errorMsg.textContent='Please enter some input.';errorMsg.style.display='block';output.style.display='none';return}}errorMsg.style.display='none';output.textContent=v;output.style.display='block'}});
        document.getElementById('clearBtn').addEventListener('click',()=>{{input.value='';output.style.display='none';errorMsg.style.display='none'}});
        document.getElementById('copyBtn').addEventListener('click',()=>{{if(!output.textContent)return;navigator.clipboard.writeText(output.textContent).then(()=>{{const b=document.getElementById('copyBtn');b.textContent='Copied!';setTimeout(()=>b.textContent='Copy Result',1500)}})}});
    </script>
</body>
</html>"""