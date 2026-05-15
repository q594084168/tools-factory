"""Search Analysis: Google Suggest scraping, tool idea scoring, template generation."""

import json
import re
import urllib.parse
from pathlib import Path
import requests

BASE_DIR = Path(__file__).parent.resolve()
TEMPLATES_DIR = BASE_DIR / "templates"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"

TOOL_SUFFIXES = [
    "compressor", "converter", "generator", "formatter", "validator",
    "counter", "editor", "viewer", "merger", "splitter", "maker",
    "creator", "remover", "resizer", "extractor", "finder", "reader",
    "checker", "downloader",
]

SCENE_POOLS = {
    "image-compress": [
        {"scenario": "Compress image for email attachment", "slug": "compress-image-for-email", "faqs": [
            {"q": "How do I compress an image for email?", "a": "Upload your image and we automatically resize it to fit within typical email attachment limits (25 MB)."},
            {"q": "What size should an email image be?", "a": "Most email providers allow up to 25 MB per attachment. We recommend keeping images under 1 MB for faster sending."},
            {"q": "Will this reduce image quality?", "a": "We use smart compression that preserves visual quality while drastically reducing file size."},
        ]},
        {"scenario": "Compress passport photo to specific KB size", "slug": "compress-passport-photo", "faqs": [
            {"q": "How many KB should a passport photo be?", "a": "Most government forms require passport photos under 240 KB. Our tool lets you set exact target sizes."},
            {"q": "Does this tool preserve photo dimensions?", "a": "Yes, compression does not change your photo's width or height, only the file size."},
            {"q": "Is this accepted for government forms?", "a": "Yes, our compression keeps the JPEG format and resolution required by most official systems."},
        ]},
        {"scenario": "Compress image for WhatsApp sharing", "slug": "compress-image-for-whatsapp", "faqs": [
            {"q": "What is WhatsApp's image size limit?", "a": "WhatsApp compresses images to 16 MB max. Pre-compressing ensures faster sending and better quality control."},
            {"q": "Why do my WhatsApp photos look blurry?", "a": "WhatsApp applies aggressive compression. Pre-compress with our tool to control the final quality."},
        ]},
        {"scenario": "Compress image for Discord upload", "slug": "compress-image-for-discord", "faqs": [
            {"q": "What is Discord's file size limit?", "a": "Free Discord accounts have an 8 MB upload limit. Nitro allows up to 500 MB."},
            {"q": "How do I send high quality images on Discord?", "a": "Compress to just under 8 MB with our tool for the best quality-to-size ratio."},
        ]},
        {"scenario": "Compress screenshot for sharing", "slug": "compress-screenshot", "faqs": [
            {"q": "How do I reduce screenshot file size?", "a": "Screenshots often contain large areas of solid color. Our tool compresses them efficiently, often reducing size by 80%."},
            {"q": "Which format is best for screenshots?", "a": "PNG for text-heavy screenshots, JPEG for photos. Our tool supports both."},
        ]},
        {"scenario": "Compress product photo for Shopify", "slug": "compress-product-photo-for-shopify", "faqs": [
            {"q": "What size should Shopify product images be?", "a": "Shopify recommends 2048 x 2048 px. Compress to under 500 KB for fast store loading."},
            {"q": "Does compression affect my product image sales?", "a": "No, our smart compression preserves product detail while improving page load speed."},
        ]},
        {"scenario": "Compress image for website performance", "slug": "compress-image-for-website", "faqs": [
            {"q": "What image size is best for web?", "a": "Aim for under 200 KB per image. Use WebP format for best compression-to-quality ratio."},
            {"q": "How does image size affect SEO?", "a": "Page speed is a Google ranking factor. Smaller images mean faster load times."},
        ]},
        {"scenario": "Compress image to exact KB size", "slug": "compress-image-to-exact-kb", "faqs": [
            {"q": "Can I compress an image to exactly 100 KB?", "a": "Yes, set your target size and our tool automatically adjusts compression quality to hit it."},
        ]},
        {"scenario": "Bulk compress multiple images at once", "slug": "bulk-image-compressor", "faqs": [
            {"q": "Can I compress many images at once?", "a": "Yes, drag and drop multiple files and compress them all in one batch."},
            {"q": "Is there a limit on how many files?", "a": "No hard limit, but we recommend batches of 50 or fewer for best performance."},
        ]},
        {"scenario": "Compress JPEG without losing quality", "slug": "compress-jpeg-without-losing-quality", "faqs": [
            {"q": "Can you compress JPEG without quality loss?", "a": "We use lossless and near-lossless compression to reduce file size with minimal quality impact."},
        ]},
        {"scenario": "Compress PNG file online", "slug": "compress-png", "faqs": [
            {"q": "How does PNG compression work?", "a": "We optimize PNG color palettes and remove unnecessary metadata while keeping transparency."},
        ]},
        {"scenario": "Compress WebP image", "slug": "compress-webp", "faqs": [
            {"q": "Can I compress WebP images further?", "a": "Yes, we can apply additional lossless or lossy compression to WebP files."},
        ]},
        {"scenario": "Compress image for Google PageSpeed", "slug": "compress-image-for-pagespeed", "faqs": [
            {"q": "Will this help my PageSpeed score?", "a": "Yes, properly compressed images are one of the most common PageSpeed recommendations."},
        ]},
        {"scenario": "Compress image for Instagram post", "slug": "compress-image-for-instagram", "faqs": [
            {"q": "What is Instagram's image size limit?", "a": "Instagram accepts up to 30 MB, but compresses uploads. Pre-compress for best quality."},
            {"q": "What resolution should Instagram photos be?", "a": "1080 px wide for square and portrait, 1080 x 566 for landscape."},
        ]},
        {"scenario": "Compress image for Facebook", "slug": "compress-image-for-facebook", "faqs": [
            {"q": "What size should Facebook images be?", "a": "Facebook recommends 1200 x 630 px for link previews and up to 2048 px for timeline photos."},
        ]},
        {"scenario": "Reduce image file size for upload form", "slug": "reduce-image-size-for-upload", "faqs": [
            {"q": "My file is too large to upload. Can you help?", "a": "Yes, compress it here first, then upload the smaller file to your form."},
        ]},
        {"scenario": "Compress signature image for email", "slug": "compress-signature-image", "faqs": [
            {"q": "What size should an email signature image be?", "a": "Aim for under 50 KB so it loads quickly in all email clients."},
        ]},
        {"scenario": "Compress icon and logo files", "slug": "compress-icon-logo", "faqs": [
            {"q": "How small should a logo file be?", "a": "Aim for under 30 KB for a logo. SVG is often better than PNG for logos."},
        ]},
        {"scenario": "Compress scanned document image", "slug": "compress-scanned-document", "faqs": [
            {"q": "Can you compress scanned PDF pages?", "a": "Yes, upload the scanned page image and we'll reduce file size while keeping text readable."},
        ]},
        {"scenario": "Compress image under 50 KB", "slug": "compress-image-under-50kb", "faqs": [
            {"q": "Can you compress to under 50 KB?", "a": "Yes, set 50 KB as your target and our tool will compress accordingly."},
        ]},
    ],
    "pdf-compress": [
        {"scenario": "Compress PDF under 1 MB", "slug": "compress-pdf-under-1mb", "faqs": [
            {"q": "Can you compress a PDF to exactly 1 MB?", "a": "Yes, set 1 MB as your target and our tool adjusts compression to hit it."},
        ]},
        {"scenario": "Compress PDF for email", "slug": "compress-pdf-for-email", "faqs": [
            {"q": "How do I send a large PDF by email?", "a": "Compress it here first. Most email providers have a 25 MB attachment limit."},
        ]},
        {"scenario": "Compress PDF without losing quality", "slug": "compress-pdf-without-losing-quality", "faqs": [
            {"q": "Will compression reduce PDF quality?", "a": "We use smart compression that shrinks file size while keeping text sharp and images clear."},
        ]},
        {"scenario": "Compress scanned PDF", "slug": "compress-scanned-pdf", "faqs": [
            {"q": "Can you compress a scanned PDF?", "a": "Yes, scanned PDFs often compress well because they contain large image data."},
        ]},
        {"scenario": "Compress PDF for upload", "slug": "compress-pdf-for-upload", "faqs": [
            {"q": "My PDF is too large for an online form. Help?", "a": "Compress it here to meet the form's size limit, then upload the smaller file."},
        ]},
    ],
    "json-formatter": [
        {"scenario": "Format JSON for debugging", "slug": "format-json-debug", "faqs": [
            {"q": "How do I make JSON readable?", "a": "Paste your minified JSON here and we pretty-print it with proper indentation."},
        ]},
        {"scenario": "Validate JSON syntax online", "slug": "validate-json-online", "faqs": [
            {"q": "How do I check if my JSON is valid?", "a": "Paste it here and we'll highlight any syntax errors with line numbers."},
        ]},
        {"scenario": "Minify JSON for production", "slug": "minify-json", "faqs": [
            {"q": "How do I remove whitespace from JSON?", "a": "Paste your formatted JSON and we strip all unnecessary spaces and newlines."},
        ]},
        {"scenario": "Convert JSON to CSV", "slug": "json-to-csv-converter", "faqs": [
            {"q": "Can I convert JSON to Excel format?", "a": "Yes, convert to CSV first, then open in Excel or Google Sheets."},
        ]},
    ],
    "qr-generator": [
        {"scenario": "Generate QR code for website URL", "slug": "qr-code-for-url", "faqs": [
            {"q": "How do I make a QR code for my website?", "a": "Enter your URL and we generate a scannable QR code instantly."},
        ]},
        {"scenario": "Create QR code for WiFi password", "slug": "wifi-qr-code", "faqs": [
            {"q": "Can I make a WiFi QR code?", "a": "Yes, enter your SSID and password. Guests scan to connect without typing."},
        ]},
        {"scenario": "Generate QR code for contact card", "slug": "vcard-qr-code", "faqs": [
            {"q": "How do I share my contact info via QR?", "a": "Enter your name, phone, and email. We generate a vCard QR code."},
        ]},
    ],
    "password-generator": [
        {"scenario": "Generate strong password for online account", "slug": "strong-password-generator", "faqs": [
            {"q": "What makes a password strong?", "a": "Length (12+ characters), mixed case, numbers, and symbols. Our generator uses all four."},
        ]},
        {"scenario": "Create memorable passphrase", "slug": "memorable-passphrase-generator", "faqs": [
            {"q": "What is a passphrase?", "a": "A sequence of random words, like 'correct-horse-battery-staple', that is easy to remember but hard to crack."},
        ]},
        {"scenario": "Generate PIN code", "slug": "pin-code-generator", "faqs": [
            {"q": "Can I generate a random 4-digit PIN?", "a": "Yes, set length to 4 digits and we generate a cryptographically random PIN."},
        ]},
    ],
    "word-counter": [
        {"scenario": "Count words for essay or assignment", "slug": "word-count-for-essay", "faqs": [
            {"q": "How do I check my essay word count?", "a": "Paste your text here and get instant word, character, and sentence counts."},
        ]},
        {"scenario": "Count characters for Twitter post", "slug": "character-count-for-twitter", "faqs": [
            {"q": "What's the Twitter character limit?", "a": "280 characters for standard tweets, 4000 for X Premium. Our counter helps you stay within limits."},
        ]},
        {"scenario": "Count words for SEO meta description", "slug": "seo-meta-description-counter", "faqs": [
            {"q": "How long should a meta description be?", "a": "Aim for 150-160 characters. Our counter helps you hit exactly that range."},
        ]},
    ],
}

SIZE_VARIANTS = {
    "image-compress": [
        {"value": 20, "unit": "KB"}, {"value": 30, "unit": "KB"}, {"value": 50, "unit": "KB"},
        {"value": 100, "unit": "KB"}, {"value": 150, "unit": "KB"}, {"value": 200, "unit": "KB"},
        {"value": 250, "unit": "KB"}, {"value": 500, "unit": "KB"}, {"value": 1, "unit": "MB"},
    ],
    "pdf-compress": [
        {"value": 1, "unit": "MB"}, {"value": 2, "unit": "MB"},
        {"value": 5, "unit": "MB"}, {"value": 10, "unit": "MB"},
    ],
}

SKELETON_CSS = """:root{--primary:#4F46E5;--primary-dark:#4338CA;--primary-light:#EEF2FF;--bg:#F8FAFC;--card-bg:#FFFFFF;--text:#1E293B;--text-secondary:#64748B;--border:#E2E8F0;--success:#10B981;--radius:12px;--radius-sm:8px;--shadow:0 1px 3px rgba(0,0,0,0.08),0 1px 2px rgba(0,0,0,0.06);--shadow-lg:0 10px 15px -3px rgba(0,0,0,0.08),0 4px 6px -2px rgba(0,0,0,0.04)}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh}
.container{max-width:960px;margin:0 auto;padding:0 24px}
header{background:#1E293B;color:#F1F5F9;padding:16px 0;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,0.15)}
header .container{display:flex;justify-content:space-between;align-items:center}
.logo{font-size:1.35rem;font-weight:700;text-decoration:none;color:#fff}.logo span{color:var(--primary)}
header nav{display:flex;gap:24px}header nav a{color:#94A3B8;text-decoration:none;font-size:.9rem;font-weight:500;transition:color .2s}header nav a:hover{color:#fff}
.hero{padding:64px 0 40px;text-align:center}.hero h1{font-size:2.5rem;font-weight:800;margin-bottom:12px;line-height:1.2}
.hero .subtitle{font-size:1.125rem;color:var(--text-secondary);max-width:560px;margin:0 auto 40px}
@media(max-width:640px){.hero h1{font-size:1.75rem}}
.tool-area{max-width:700px;margin:0 auto 24px}
.tool-area textarea,.tool-area input[type="text"]{width:100%;border:2px dashed var(--border);border-radius:var(--radius);padding:20px;font-family:'Consolas',monospace;font-size:14px;resize:vertical;background:var(--card-bg);min-height:200px}
.tool-area textarea:focus,.tool-area input:focus{outline:none;border-color:var(--primary);border-style:solid}
.btn-row{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:24px}
.btn{padding:12px 28px;border:none;border-radius:var(--radius-sm);font-size:1rem;font-weight:600;cursor:pointer;transition:all .2s;font-family:inherit}.btn:active{transform:scale(.97)}
.btn-primary{background:var(--primary);color:#fff;box-shadow:var(--shadow)}.btn-primary:hover{background:var(--primary-dark);box-shadow:var(--shadow-lg)}
.btn-secondary{background:var(--card-bg);color:var(--text);border:1px solid var(--border)}.btn-secondary:hover{background:var(--bg)}
.output-area{margin-top:16px;background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);padding:20px;min-height:80px;word-break:break-all;display:none}
.error-msg{color:#DC2626;font-size:.85rem;margin-top:8px;display:none}
.ad-slot{background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);min-height:90px;display:flex;align-items:center;justify-content:center;max-width:728px;margin:0 auto 24px}
.ad-placeholder{color:var(--border);font-size:.8rem;text-transform:uppercase;letter-spacing:.1em}
.how-section{padding:60px 0;background:var(--card-bg);border-top:1px solid var(--border);text-align:center}
.how-section h2{font-size:2rem;margin-bottom:48px}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:32px;max-width:900px;margin:0 auto}
@media(max-width:640px){.steps{grid-template-columns:1fr}}
.step__num{width:48px;height:48px;border-radius:50%;background:var(--primary);color:#fff;font-size:1.25rem;font-weight:700;display:flex;align-items:center;justify-content:center;margin:0 auto 16px}
.step h3{font-size:1.1rem;margin-bottom:8px}.step p{font-size:.9rem;color:var(--text-secondary)}
.faq-section{padding:60px 0;text-align:left}.faq-section h2{font-size:2rem;margin-bottom:32px;text-align:center}
.faq-item{margin-bottom:24px}.faq-item h3{font-size:1.05rem;margin-bottom:6px;color:var(--primary)}
.faq-item p{color:var(--text-secondary);font-size:.95rem}
footer{background:#1E293B;color:#94A3B8;padding:32px 0;text-align:center;font-size:.85rem}
footer a{color:#CBD5E1;text-decoration:none}footer a:hover{color:#fff}"""


def fetch_suggestions(keyword):
    """Fetch autocomplete suggestions from Google Suggest. Returns list of strings."""
    try:
        url = f"https://suggestqueries.google.com/complete/search?client=chrome&q={urllib.parse.quote(keyword)}"
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=10)
        if resp.status_code != 200:
            return []
        text = resp.text

        # Try direct JSON first (client=chrome returns plain JSON)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Fallback: strip JSONP wrapper
            match = re.search(r"window\.google\.ac\.h\((.*)\)\s*$", text, re.DOTALL)
            if not match:
                return []
            data = json.loads(match.group(1))

        if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
            return [s for s in data[1] if isinstance(s, str)]
        return []
    except Exception:
        return []


def analyze_seed(seed_keyword):
    """Generate tool ideas from seed keyword, validate against Google Suggest, return scored results."""
    seed = seed_keyword.strip().lower()
    if not seed:
        raise ValueError("Seed keyword is empty")

    results = []
    candidates = []

    # Build candidates: "<seed> <suffix>" and "<suffix> <seed>"
    for suffix in TOOL_SUFFIXES:
        candidates.append((" ".join([seed, suffix]), seed, suffix))
        # suffix-first patterns that make grammatical sense
        if suffix not in ("maker", "creator", "downloader", "finder", "reader", "checker"):
            candidates.append((" ".join([suffix, seed]), seed, suffix))

    tested = 0
    for idea, s, suffix in candidates:
        tested += 1
        suggestions = fetch_suggestions(idea)
        idea_lower = idea.lower()

        score = 0
        demand = 0
        match_type = "none"

        if suggestions:
            # Check for exact match
            exact_match = any(idea_lower == sug.lower() for sug in suggestions)
            if exact_match:
                score = 100
                match_type = "exact"
            # Check for substring match
            elif any(idea_lower in sug.lower() for sug in suggestions):
                score = 80
                match_type = "substring"
            # Check for partial (both seed and suffix appear in same suggestion)
            elif any(s.lower() in sug.lower() and suffix.lower() in sug.lower() for sug in suggestions):
                score = 60
                match_type = "partial"
            # At least one suggestion contains the seed
            elif any(s.lower() in sug.lower() for sug in suggestions):
                score = 40
                match_type = "seed_matched"
            else:
                score = 10
                match_type = "none"

            # Demand signal: what fraction of suggestions relate to our terms
            related = sum(1 for sug in suggestions if s.lower() in sug.lower())
            demand = min(int(related / len(suggestions) * 100), 100)
        else:
            match_type = "no_data"

        results.append({
            "idea": idea,
            "seed": s,
            "suffix": suffix,
            "score": score,
            "demand": demand,
            "match_type": match_type,
            "raw_suggestions": suggestions[:8],
        })

    results.sort(key=lambda x: (x["score"], x["demand"]), reverse=True)
    return results, tested


def generate_scene_variants(template_type, count=50):
    """Generate scene-targeted keyword variants for a tool type.

    Returns list of dicts:
        {slug, title, description, scenario, faqs, parent_template}
    """
    meta_path = TEMPLATES_DIR / template_type / "meta.json"
    tool_title = template_type.replace("-", " ").title()
    tool_description = f"Free online {template_type} tool."
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        tool_title = meta.get("tool_title", tool_title)
        tool_description = meta.get("tool_description", tool_description)

    pool = SCENE_POOLS.get(template_type, [])
    size_variants = SIZE_VARIANTS.get(template_type, [])

    results = []

    for entry in pool[:count]:
        slug = entry["slug"]
        title = f"{entry['scenario']} — Free Online | {tool_title}"
        desc = f"{entry['scenario']}. {tool_description} No signup required. Works in your browser."
        results.append({
            "slug": slug,
            "title": title,
            "description": desc,
            "scenario": entry["scenario"],
            "faqs": entry.get("faqs", []),
            "parent_template": template_type,
        })

    # Derive tool noun and verb from template_type for size-variant slugs
    tool_noun = template_type.split("-")[0]  # "image", "pdf", etc.
    tool_verb = "Compress" if "compress" in template_type else tool_noun.capitalize()

    for sv in size_variants:
        if len(results) >= count:
            break
        v = sv["value"]
        unit = sv["unit"]
        unit_slug = unit.lower()
        label = f"{v} {unit}"
        slug = f"compress-{tool_noun}-to-{v}{unit_slug}"
        title = f"{tool_verb} {tool_noun.capitalize()} to {label} Online Free | {tool_title}"
        desc = f"Compress any {tool_noun} to exactly {label}. {tool_description}"
        results.append({
            "slug": slug,
            "title": title,
            "description": desc,
            "scenario": f"Compress {tool_noun} to {label}",
            "faqs": [
                {"q": f"Can I compress a {tool_noun} to exactly {label}?", "a": f"Yes. Upload your {tool_noun} and set {label} as the target size. Our tool adjusts compression to hit your target."},
                {"q": "Is this tool free?", "a": "Yes, completely free. No signup or credit card required."},
                {"q": "Does it work on mobile?", "a": "Yes, works on phones, tablets, and desktop browsers."},
            ],
            "parent_template": template_type,
        })

    return results


def _slugify(name):
    """Convert a name into a URL/filesystem-safe slug."""
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:50]


def create_template(idea_name, tool_title, tool_description, keywords_primary, suffixes_list):
    """Create template files for a new tool type. Returns result dict."""
    slug = _slugify(idea_name)
    if not slug:
        raise ValueError(f"Invalid idea name: '{idea_name}'")

    template_dir = TEMPLATES_DIR / slug
    if template_dir.exists():
        return {"success": False, "error": f"模板 '{slug}' 已存在"}

    template_dir.mkdir(parents=True)

    # Build keyword file
    tlds = [".com", ".net", ".io"]
    keywords = {
        "primary": list(set(p.lower() for p in keywords_primary if p)),
        "suffixes": list(set(s.lower() for s in suffixes_list if s)),
        "tlds": tlds,
    }

    # Build meta file
    meta = {
        "name": " ".join(w.capitalize() for w in idea_name.split()),
        "tool_title": tool_title,
        "tool_description": tool_description,
    }

    # Write files
    files_created = []

    html = _build_template_html()
    with open(template_dir / "template.html", "w", encoding="utf-8") as f:
        f.write(html)
    files_created.append("template.html")

    with open(template_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    files_created.append("meta.json")

    with open(template_dir / "keywords.json", "w", encoding="utf-8") as f:
        json.dump(keywords, f, indent=2, ensure_ascii=False)
    files_created.append("keywords.json")

    return {
        "success": True,
        "template_slug": slug,
        "template_dir": str(template_dir),
        "files_created": files_created,
        "message": f"Template created. Refresh the page to see it in the template list.",
    }


def _build_template_html():
    """Generate SEO-rich template HTML skeleton matching existing tool template style."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{{{{TOOL_DESCRIPTION}}}}">
    <meta name="robots" content="index, follow">
    <meta property="og:title" content="{{{{TOOL_TITLE}}}} — {{{{SITE_NAME}}}}">
    <meta property="og:description" content="{{{{TOOL_DESCRIPTION}}}}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{{{CANONICAL_URL}}}}">
    <meta property="og:site_name" content="{{{{SITE_NAME}}}}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{{{{TOOL_TITLE}}}} — {{{{SITE_NAME}}}}">
    <meta name="twitter:description" content="{{{{TOOL_DESCRIPTION}}}}">
    <link rel="canonical" href="{{{{CANONICAL_URL}}}}">
    <title>{{{{TOOL_TITLE}}}} — {{{{SITE_NAME}}}}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%234F46E5'/%3E%3Ctext x='50' y='72' font-size='60' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'%3ET%3C/text%3E%3C/svg%3E">
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": "{{{{TOOL_TITLE}}}}",
        "url": "{{{{CANONICAL_URL}}}}",
        "description": "{{{{TOOL_DESCRIPTION}}}}",
        "applicationCategory": "UtilityApplication",
        "operatingSystem": "All",
        "offers": {{ "@type": "Offer", "price": "0", "priceCurrency": "USD" }}
    }}
    </script>
    {{{{GA_ID}}}}
    <style>
        {SKELETON_CSS}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <a href="/" class="logo"><span>T</span> {{{{SITE_NAME}}}}</a>
            <nav>
                <a href="/">Home</a>
                <a href="#how">How It Works</a>
                <a href="#faq">FAQ</a>
            </nav>
        </div>
    </header>
    <main>
        <section class="hero">
            <div class="container">
                <h1>{{{{TOOL_TITLE}}}}</h1>
                <p class="subtitle">{{{{TOOL_DESCRIPTION}}}}</p>
                <div class="tool-area">
                    <textarea id="toolInput" placeholder="Paste or type your input here..."></textarea>
                    <div class="output-area" id="toolOutput"></div>
                    <p class="error-msg" id="errorMsg"></p>
                </div>
                <div class="btn-row">
                    <button class="btn btn-primary" id="actionBtn">Process</button>
                    <button class="btn btn-secondary" id="clearBtn">Clear</button>
                    <button class="btn btn-secondary" id="copyBtn">Copy Result</button>
                </div>
                <div class="ad-slot"><div class="ad-placeholder">Advertisement</div></div>
            </div>
        </section>
        <section class="how-section" id="how">
            <div class="container">
                <h2>How It Works</h2>
                <div class="steps">
                    <div class="step"><div class="step__num">1</div><h3>Input</h3><p>Paste or type your content into the tool above.</p></div>
                    <div class="step"><div class="step__num">2</div><h3>Process</h3><p>Click the button and your content is processed instantly.</p></div>
                    <div class="step"><div class="step__num">3</div><h3>Copy & Use</h3><p>Copy the result with one click. Everything happens locally.</p></div>
                </div>
            </div>
        </section>
        <section class="faq-section" id="faq">
            <div class="container">
                <h2>Frequently Asked Questions</h2>
                <div class="faq-item">
                    <h3>Is {{{{TOOL_TITLE}}}} free?</h3>
                    <p>Yes — completely free. No signup, no credit card required.</p>
                </div>
                <div class="faq-item">
                    <h3>Is my data safe?</h3>
                    <p>All processing happens locally in your browser. Your data is never uploaded to any server.</p>
                </div>
                <div class="faq-item">
                    <h3>Does it work on mobile?</h3>
                    <p>Yes. {{{{SITE_NAME}}}} is fully responsive and works on phones, tablets, and desktops.</p>
                </div>
            </div>
        </section>
    </main>
    <footer>
        <div class="container">
            <p>&copy; 2026 {{{{SITE_NAME}}}}. All rights reserved. | <a href="/">Home</a> | <a href="#faq">FAQ</a></p>
            <p style="margin-top:8px">All processing happens locally in your browser. Your data is never uploaded.</p>
        </div>
    </footer>
    <script>
        const input = document.getElementById('toolInput');
        const output = document.getElementById('toolOutput');
        const errorMsg = document.getElementById('errorMsg');

        document.getElementById('actionBtn').addEventListener('click', () => {{
            const val = input.value.trim();
            if (!val) {{
                errorMsg.textContent = 'Please enter some input.';
                errorMsg.style.display = 'block';
                output.style.display = 'none';
                return;
            }}
            errorMsg.style.display = 'none';
            // TODO: Replace with actual tool logic
            output.textContent = val;
            output.style.display = 'block';
        }});

        document.getElementById('clearBtn').addEventListener('click', () => {{
            input.value = '';
            output.style.display = 'none';
            errorMsg.style.display = 'none';
        }});

        document.getElementById('copyBtn').addEventListener('click', () => {{
            if (!output.textContent) return;
            navigator.clipboard.writeText(output.textContent).then(() => {{
                const b = document.getElementById('copyBtn');
                b.textContent = 'Copied!';
                setTimeout(() => b.textContent = 'Copy Result', 1500);
            }});
        }});
    </script>
</body>
</html>"""
