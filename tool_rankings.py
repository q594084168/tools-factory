"""Tool Ranking Engine — tracks search interest for known online tool types via Google Suggest."""

import json
import time
from datetime import datetime
from pathlib import Path
from search_analyzer import fetch_suggestions

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
RANKINGS_FILE = DATA_DIR / "tool_rankings.json"

# Comprehensive list of known online tools
KNOWN_TOOLS = [
    # --- Image Tools ---
    {"name": "Image Compressor", "category": "Image", "query": "image compressor"},
    {"name": "Image Converter", "category": "Image", "query": "image converter"},
    {"name": "Image Resizer", "category": "Image", "query": "image resizer"},
    {"name": "Image Cropper", "category": "Image", "query": "image cropper"},
    {"name": "Image Editor", "category": "Image", "query": "image editor"},
    {"name": "Image to PDF", "category": "Image", "query": "image to pdf"},
    {"name": "PNG to JPG", "category": "Image", "query": "png to jpg"},
    {"name": "JPG to PNG", "category": "Image", "query": "jpg to png"},
    {"name": "HEIC to JPG", "category": "Image", "query": "heic to jpg"},
    {"name": "Background Remover", "category": "Image", "query": "background remover"},
    {"name": "Image Upscaler", "category": "Image", "query": "image upscaler"},
    {"name": "Photo Editor", "category": "Image", "query": "photo editor"},
    {"name": "Screenshot Tool", "category": "Image", "query": "screenshot tool"},
    {"name": "Favicon Generator", "category": "Image", "query": "favicon generator"},

    # --- PDF Tools ---
    {"name": "PDF Compressor", "category": "PDF", "query": "pdf compressor"},
    {"name": "PDF Merger", "category": "PDF", "query": "pdf merger"},
    {"name": "PDF Splitter", "category": "PDF", "query": "pdf splitter"},
    {"name": "PDF Editor", "category": "PDF", "query": "pdf editor"},
    {"name": "PDF to Word", "category": "PDF", "query": "pdf to word"},
    {"name": "Word to PDF", "category": "PDF", "query": "word to pdf"},
    {"name": "PDF to JPG", "category": "PDF", "query": "pdf to jpg"},
    {"name": "PDF Viewer", "category": "PDF", "query": "pdf viewer"},
    {"name": "PDF Converter", "category": "PDF", "query": "pdf converter"},
    {"name": "PDF Signer", "category": "PDF", "query": "pdf signer"},
    {"name": "PDF Unlocker", "category": "PDF", "query": "pdf unlocker"},
    {"name": "PDF OCR", "category": "PDF", "query": "pdf ocr"},

    # --- Text Tools ---
    {"name": "Word Counter", "category": "Text", "query": "word counter"},
    {"name": "Character Counter", "category": "Text", "query": "character counter"},
    {"name": "Text Formatter", "category": "Text", "query": "text formatter"},
    {"name": "Text Compare", "category": "Text", "query": "text compare"},
    {"name": "Text to Speech", "category": "Text", "query": "text to speech"},
    {"name": "Plagiarism Checker", "category": "Text", "query": "plagiarism checker"},
    {"name": "Grammar Checker", "category": "Text", "query": "grammar checker"},
    {"name": "Case Converter", "category": "Text", "query": "case converter"},
    {"name": "Lorem Ipsum Generator", "category": "Text", "query": "lorem ipsum generator"},
    {"name": "Diff Checker", "category": "Text", "query": "diff checker"},

    # --- Developer Tools ---
    {"name": "JSON Formatter", "category": "Developer", "query": "json formatter"},
    {"name": "JSON Validator", "category": "Developer", "query": "json validator"},
    {"name": "JSON to CSV", "category": "Developer", "query": "json to csv"},
    {"name": "XML Formatter", "category": "Developer", "query": "xml formatter"},
    {"name": "HTML Formatter", "category": "Developer", "query": "html formatter"},
    {"name": "CSS Formatter", "category": "Developer", "query": "css formatter"},
    {"name": "JavaScript Formatter", "category": "Developer", "query": "javascript formatter"},
    {"name": "Base64 Encoder", "category": "Developer", "query": "base64 encoder"},
    {"name": "Base64 Decoder", "category": "Developer", "query": "base64 decoder"},
    {"name": "URL Encoder", "category": "Developer", "query": "url encoder"},
    {"name": "URL Decoder", "category": "Developer", "query": "url decoder"},
    {"name": "Markdown Editor", "category": "Developer", "query": "markdown editor"},
    {"name": "SQL Formatter", "category": "Developer", "query": "sql formatter"},
    {"name": "Minifier", "category": "Developer", "query": "minifier"},
    {"name": "UUID Generator", "category": "Developer", "query": "uuid generator"},
    {"name": "Hash Generator", "category": "Developer", "query": "hash generator"},
    {"name": "Regex Tester", "category": "Developer", "query": "regex tester"},
    {"name": "Code Beautifier", "category": "Developer", "query": "code beautifier"},

    # --- Video Tools ---
    {"name": "Video Compressor", "category": "Video", "query": "video compressor"},
    {"name": "Video Converter", "category": "Video", "query": "video converter"},
    {"name": "Video Editor", "category": "Video", "query": "video editor"},
    {"name": "MP4 Converter", "category": "Video", "query": "mp4 converter"},
    {"name": "YouTube Downloader", "category": "Video", "query": "youtube downloader"},
    {"name": "Screen Recorder", "category": "Video", "query": "screen recorder"},
    {"name": "GIF Maker", "category": "Video", "query": "gif maker"},
    {"name": "Video Merger", "category": "Video", "query": "video merger"},
    {"name": "Video Trimmer", "category": "Video", "query": "video trimmer"},
    {"name": "Subtitles Generator", "category": "Video", "query": "subtitles generator"},

    # --- Audio Tools ---
    {"name": "Audio Converter", "category": "Audio", "query": "audio converter"},
    {"name": "MP3 Converter", "category": "Audio", "query": "mp3 converter"},
    {"name": "Audio Compressor", "category": "Audio", "query": "audio compressor"},
    {"name": "Voice Recorder", "category": "Audio", "query": "voice recorder"},
    {"name": "Audio to Text", "category": "Audio", "query": "audio to text"},
    {"name": "Text to MP3", "category": "Audio", "query": "text to mp3"},

    # --- Generators ---
    {"name": "QR Code Generator", "category": "Generator", "query": "qr code generator"},
    {"name": "Password Generator", "category": "Generator", "query": "password generator"},
    {"name": "Random Number Generator", "category": "Generator", "query": "random number generator"},
    {"name": "Barcode Generator", "category": "Generator", "query": "barcode generator"},
    {"name": "Signature Generator", "category": "Generator", "query": "signature generator"},
    {"name": "Email Generator", "category": "Generator", "query": "email generator"},
    {"name": "Name Generator", "category": "Generator", "query": "name generator"},
    {"name": "Color Palette Generator", "category": "Generator", "query": "color palette generator"},

    # --- Converters ---
    {"name": "Unit Converter", "category": "Converter", "query": "unit converter"},
    {"name": "Currency Converter", "category": "Converter", "query": "currency converter"},
    {"name": "Time Zone Converter", "category": "Converter", "query": "time zone converter"},
    {"name": "File Converter", "category": "Converter", "query": "file converter"},
    {"name": "CSV to JSON", "category": "Converter", "query": "csv to json"},
    {"name": "YAML to JSON", "category": "Converter", "query": "yaml to json"},
    {"name": "HTML to PDF", "category": "Converter", "query": "html to pdf"},

    # --- Calculators ---
    {"name": "Percentage Calculator", "category": "Calculator", "query": "percentage calculator"},
    {"name": "BMI Calculator", "category": "Calculator", "query": "bmi calculator"},
    {"name": "Age Calculator", "category": "Calculator", "query": "age calculator"},
    {"name": "Mortgage Calculator", "category": "Calculator", "query": "mortgage calculator"},
    {"name": "Tip Calculator", "category": "Calculator", "query": "tip calculator"},
    {"name": "Loan Calculator", "category": "Calculator", "query": "loan calculator"},
    {"name": "Scientific Calculator", "category": "Calculator", "query": "scientific calculator"},

    # --- SEO / Web ---
    {"name": "Meta Tag Generator", "category": "SEO", "query": "meta tag generator"},
    {"name": "Sitemap Generator", "category": "SEO", "query": "sitemap generator"},
    {"name": "Robots.txt Generator", "category": "SEO", "query": "robots.txt generator"},
    {"name": "WHOIS Lookup", "category": "SEO", "query": "whois lookup"},
    {"name": "IP Lookup", "category": "SEO", "query": "ip lookup"},
    {"name": "DNS Lookup", "category": "SEO", "query": "dns lookup"},
    {"name": "Website Speed Test", "category": "SEO", "query": "website speed test"},
    {"name": "SSL Checker", "category": "SEO", "query": "ssl checker"},
]


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_rankings():
    """Load cached rankings from disk."""
    _ensure_dir()
    if RANKINGS_FILE.exists():
        with open(RANKINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": None, "tools": []}


def save_rankings(data):
    """Save rankings to disk."""
    _ensure_dir()
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(RANKINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _extract_seed_and_term(query):
    """Extract category seed word and tool-specific term from a query.
    e.g., 'image compressor' → ('image', 'compressor')
          'pdf to word' → ('pdf', 'to word')
          'json formatter' → ('json', 'formatter')
    """
    parts = query.split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return parts[0], ""


def refresh_rankings():
    """Multi-pass ranking with positional scoring across seed variants.

    Google Suggest always returns ~15 suggestions regardless of popularity,
    so counting suggestions doesn't differentiate. Instead we query multiple
    seed variants ("online {seed}", "{seed} tool", "free {seed}") and score
    each tool by WHERE its term appears — earlier position = higher demand.
    Averaging across variants + variant coverage produces granular scores.
    """
    _ensure_dir()
    old_data = load_rankings()
    old_map = {t["name"]: t for t in old_data.get("tools", [])}

    # Group tools by seed (first word of query)
    seed_groups = {}
    for tool in KNOWN_TOOLS:
        seed, _ = _extract_seed_and_term(tool["query"])
        if seed not in seed_groups:
            seed_groups[seed] = []
        seed_groups[seed].append(tool)

    # Pass 1: Query 3 seed variants per unique seed for richer signal
    seed_variants = [
        "online {}",
        "{} tool",
        "free {}",
    ]
    unique_seeds = list(seed_groups.keys())

    category_suggestions = {}  # {seed: {variant_idx: [suggestions]}}
    for seed_idx, seed in enumerate(unique_seeds):
        category_suggestions[seed] = {}
        for vi, variant_template in enumerate(seed_variants):
            query = variant_template.format(seed)
            suggestions = fetch_suggestions(query)
            category_suggestions[seed][vi] = [s.lower() for s in suggestions]
            time.sleep(0.25)

    # Pass 2: Score each tool with positional + coverage signals
    tools = []
    total = len(KNOWN_TOOLS)
    for i, tool in enumerate(KNOWN_TOOLS):
        seed, term = _extract_seed_and_term(tool["query"])
        term_lower = term.lower()
        term_parts = term_lower.split()

        # Direct suggestion count (for display + tiebreaker)
        s1 = fetch_suggestions(tool["query"])
        c1 = len(s1)

        # Positional scoring across seed variants
        raw_positions = []  # 0-indexed position per variant where term was found
        variant_found = 0

        for vi in range(len(seed_variants)):
            suggestions = category_suggestions.get(seed, {}).get(vi, [])
            found_pos = None
            for pos, sug in enumerate(suggestions):
                if term_lower in sug:
                    found_pos = pos
                    break
                elif term_parts and all(p in sug for p in term_parts):
                    found_pos = pos
                    break
            if found_pos is not None:
                raw_positions.append(found_pos)
                variant_found += 1

        # Exponential position decay: 1st place = 100, 5th = 24, 10th = 5.6, 15th = 1.8
        # Much steeper than linear to spread scores apart
        exp_scores = [100 * (0.75 ** p) for p in raw_positions]

        # Average exponential score across variants where term was found
        avg_exp_score = sum(exp_scores) / len(exp_scores) if exp_scores else 0

        # Coverage bonus: appearing in more variants = broader real demand (0-36)
        coverage_bonus = variant_found * 12

        # Specific tiebreaker: suggestion count with diminishing returns (0-5)
        specific_bonus = min(c1, 10) * 0.5

        # Category hit count for display purposes
        all_cat = []
        for vi in range(len(seed_variants)):
            all_cat.extend(category_suggestions.get(seed, {}).get(vi, []))
        category_hits = sum(
            1 for sug in all_cat
            if term_lower in sug or (term_parts and all(p in sug for p in term_parts))
        )

        # Raw position for display (0-indexed average, lower = better)
        avg_raw_pos = sum(raw_positions) / len(raw_positions) if raw_positions else None

        # Composite: exp_position 0-65 + coverage 0-36 + specific 0-5 = 0-106
        interest_score = min(round(avg_exp_score * 0.65 + coverage_bonus + specific_bonus), 100)

        old_tool = old_map.get(tool["name"], {})
        old_score = old_tool.get("interest_score", 0)
        if old_score > 0:
            change = interest_score - old_score
            trend = "up" if change > 5 else ("down" if change < -5 else "stable")
        else:
            trend = "new"

        # Merge suggestions from all seed variants for richer display
        merged = []
        for vi in range(len(seed_variants)):
            for sug in category_suggestions.get(seed, {}).get(vi, []):
                if term_lower in sug or (term_parts and all(p in sug for p in term_parts)):
                    merged.append(sug)
        merged += [s for s in s1 if s]
        all_suggestions = list(dict.fromkeys(merged))[:5]

        tools.append({
            "name": tool["name"],
            "category": tool["category"],
            "query": tool["query"],
            "interest_score": interest_score,
            "suggestion_count": c1,
            "category_hits": category_hits,
            "variant_found": variant_found,
            "avg_raw_pos": round(avg_raw_pos, 1) if avg_raw_pos is not None else None,
            "trend": trend,
            "top_suggestions": all_suggestions,
        })

        if i < total - 1:
            time.sleep(0.25)

    tools.sort(key=lambda x: x["interest_score"], reverse=True)
    for idx, t in enumerate(tools):
        t["rank"] = idx + 1

    data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_tools": len(tools),
        "tools": tools,
    }
    save_rankings(data)
    return data


def get_rankings(category=None, force_refresh=False):
    """Get current rankings, optionally filtered by category. Refreshes if cache is stale or forced."""
    data = load_rankings()

    # Refresh if stale (over 24h) or forced
    if force_refresh or not data.get("tools") or _is_stale(data):
        data = refresh_rankings()

    tools = data.get("tools", [])
    if category:
        tools = [t for t in tools if t["category"] == category]

    return {
        "last_updated": data.get("last_updated"),
        "total_tools": len(tools),
        "categories": sorted(set(t["category"] for t in data.get("tools", []))),
        "tools": tools,
    }


def _is_stale(data):
    """Check if rankings data is older than 24 hours."""
    last = data.get("last_updated")
    if not last:
        return True
    try:
        last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - last_dt).total_seconds() > 86400  # 24h
    except Exception:
        return True
