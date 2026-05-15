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

    # Inject scene navigation into homepage
    if scene_pages:
        index_path = output_dir / "index.html"
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
            nav_html = _build_scene_nav(scene_pages, domain)
            if "</main>" in content:
                content = content.replace("</main>", nav_html + "\n</main>")
            else:
                content = content.replace("</body>", nav_html + "\n</body>")
            with open(index_path, "w", encoding="utf-8") as f:
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
        html = _build_scene_page(scene, replacements, scene_pages, template_type)
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


def _build_scene_nav(scene_pages, domain):
    """Build HTML block with links to all scene pages for homepage navigation."""
    links = ""
    for scene in scene_pages:
        title = html.escape(scene["title"])
        desc = html.escape(scene.get("scenario", title))
        links += f'                <li><a href="/{scene["slug"]}/"><strong>{title}</strong><span>{desc}</span></a></li>\n'
    return f"""        <section class="scene-nav" id="scenes">
            <div class="container">
                <h2>Free Online Image Tools</h2>
                <p class="subtitle">More specialized tools for your specific needs</p>
                <ul class="scene-grid">
{links}                </ul>
            </div>
        </section>
        <style>
            .scene-nav{{padding:60px 0;background:#fff;border-top:1px solid #e2e8f0}}
            .scene-nav h2{{text-align:center;font-size:2rem;margin-bottom:12px}}
            .scene-nav .subtitle{{text-align:center;color:#64748b;margin-bottom:40px}}
            .scene-grid{{list-style:none;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;max-width:960px;margin:0 auto;padding:0 24px}}
            .scene-grid li{{}}
            .scene-grid a{{display:block;padding:16px 20px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;text-decoration:none;transition:all .15s}}
            .scene-grid a:hover{{border-color:#2563eb;box-shadow:0 4px 12px rgba(37,99,235,0.1);transform:translateY(-1px)}}
            .scene-grid strong{{display:block;color:#1e293b;font-size:1rem;margin-bottom:4px}}
            .scene-grid span{{display:block;color:#64748b;font-size:.85rem}}
        </style>"""


def _build_sitemap(domain, scene_pages):
    """Build sitemap.xml listing homepage + all scene sub-pages."""
    urls = [f"  <url>\n    <loc>https://{domain}/</loc>\n    <changefreq>monthly</changefreq>\n    <priority>1.0</priority>\n  </url>"]
    for scene in scene_pages:
        urls.append(f"  <url>\n    <loc>https://{domain}/{scene['slug']}/</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"


def _img_tool_css():
    return """
        .tool-area{max-width:700px;margin:0 auto 24px;padding:0 24px}
        .upload-zone{border:2px dashed #CBD5E1;border-radius:12px;padding:40px 24px;cursor:pointer;text-align:center;transition:border-color .2s,background .2s;background:#fff}
        .upload-zone:hover,.upload-zone.drag-over{border-color:#4F46E5;background:#EEF2FF}
        .upload-zone svg{color:#4F46E5;margin-bottom:12px}
        .upload-zone__text{font-size:1rem;margin-bottom:4px;color:#1E293B}
        .upload-zone__formats{font-size:.82rem;color:#94A3B8}
        .preview-row{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px}
        @media(max-width:640px){.preview-row{grid-template-columns:1fr}}
        .preview-card{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:16px;text-align:center;min-height:200px;display:flex;flex-direction:column;align-items:center;justify-content:center}
        .preview-card h3{font-size:.8rem;color:#64748B;text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px}
        .preview-card img{max-width:100%;max-height:260px;border-radius:8px;object-fit:contain}
        .preview-card .file-info{font-size:.8rem;color:#64748B;margin-top:10px}
        .batch-list{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
        .batch-chip{background:#EEF2FF;border:1px solid #C7D2FE;border-radius:20px;padding:4px 12px;font-size:.8rem;display:flex;align-items:center;gap:6px;cursor:pointer}
        .batch-chip .remove{color:#EF4444;font-weight:700;cursor:pointer;font-size:1rem}
        .batch-chip.active{background:#4F46E5;color:#fff;border-color:#4F46E5}
        .control-row{display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:center;margin-bottom:16px}
        .quality-control{display:flex;align-items:center;gap:8px;min-width:200px}
        .quality-control label{font-weight:600;font-size:.9rem;white-space:nowrap}
        .quality-control input[type=range]{flex:1;accent-color:#4F46E5}
        .mode-toggle{display:flex;gap:4px;background:#F1F5F9;border-radius:8px;padding:3px}
        .mode-toggle button{padding:6px 14px;border:none;border-radius:6px;font-size:.82rem;font-weight:500;cursor:pointer;background:transparent;color:#64748B}
        .mode-toggle button.active{background:#4F46E5;color:#fff}
        .target-input{display:flex;align-items:center;gap:6px}
        .target-input input{width:70px;padding:8px 10px;border:1px solid #CBD5E1;border-radius:8px;font-size:.9rem;text-align:center}
        .target-input span{font-size:.85rem;color:#64748B}
        .format-select select{padding:8px 12px;border:1px solid #CBD5E1;border-radius:8px;font-size:.85rem;background:#fff}
        .compression-stats{display:flex;justify-content:center;gap:32px;flex-wrap:wrap;margin-bottom:8px}
        .stat{text-align:center}.stat__label{display:block;font-size:.8rem;color:#64748B}.stat__value{font-size:1.3rem;font-weight:700}
        .stat__value--highlight{color:#16A34A}
        .btn-row{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-bottom:20px}
        .btn{padding:10px 24px;border:none;border-radius:8px;font-size:.9rem;font-weight:600;cursor:pointer;font-family:inherit;transition:all .15s}
        .btn:active{transform:scale(.97)}.btn:disabled{opacity:.5;cursor:not-allowed}
        .btn-primary{background:#4F46E5;color:#fff}.btn-primary:hover:not(:disabled){background:#4338CA}
        .btn-success{background:#16A34A;color:#fff}.btn-success:hover:not(:disabled){background:#15803D}
        .btn-outline{background:#fff;color:#1E293B;border:1px solid #CBD5E1}.btn-outline:hover{background:#F8FAFC}
        .progress-bar{width:100%;height:6px;background:#E2E8F0;border-radius:3px;margin-bottom:8px;overflow:hidden;display:none}
        .progress-bar .fill{height:100%;background:#4F46E5;border-radius:3px;transition:width .3s;width:0%}
        .toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1E293B;color:#fff;padding:12px 24px;border-radius:8px;font-size:.9rem;z-index:999;opacity:0;transition:opacity .3s;pointer-events:none}
        .toast.show{opacity:1}
        .file-count{text-align:center;font-size:.85rem;color:#64748B;margin-bottom:8px}
    """

def _img_tool_js(preset_target_kb=""):
    return f"""<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    <script>
    (function(){{
        'use strict';
        var uploadZone=document.getElementById('uploadZone'),fileInput=document.getElementById('fileInput'),compressBtn=document.getElementById('compressBtn'),downloadBtn=document.getElementById('downloadBtn'),downloadAllBtn=document.getElementById('downloadAllBtn'),qualitySlider=document.getElementById('qualitySlider'),qualityValue=document.getElementById('qualityValue'),previewImage=document.getElementById('previewImage'),compressedPreview=document.getElementById('compressedPreview'),originalInfo=document.getElementById('originalInfo'),compressedInfo=document.getElementById('compressedInfo'),compressionStats=document.getElementById('compressionStats'),controls=document.getElementById('controls'),origSizeEl=document.getElementById('origSize'),compSizeEl=document.getElementById('compSize'),savedPercent=document.getElementById('savedPercent'),modeQuality=document.getElementById('modeQuality'),modeTarget=document.getElementById('modeTarget'),targetGroup=document.getElementById('targetGroup'),qualityGroup=document.getElementById('qualityGroup'),targetSizeInput=document.getElementById('targetSizeInput'),formatSelect=document.getElementById('formatSelect'),batchList=document.getElementById('batchList'),fileCount=document.getElementById('fileCount'),progressBar=document.getElementById('progressBar'),progressFill=document.getElementById('progressFill');
        var files=[],compressedResults=[],currentFileIdx=0,currentMode='quality';
        var presetTarget='{preset_target_kb}';

        function formatSize(b){{if(b<1024)return b+' B';if(b<1048576)return(b/1024).toFixed(1)+' KB';return(b/1048576).toFixed(2)+' MB'}}

        function showToast(m){{var t=document.getElementById('toast');t.textContent=m;t.classList.add('show');clearTimeout(t._t);t._t=setTimeout(function(){{t.classList.remove('show')}},2500)}}

        uploadZone.addEventListener('click',function(){{fileInput.click()}});
        uploadZone.addEventListener('dragover',function(e){{e.preventDefault();uploadZone.classList.add('drag-over')}});
        uploadZone.addEventListener('dragleave',function(e){{e.preventDefault();uploadZone.classList.remove('drag-over')}});
        uploadZone.addEventListener('drop',function(e){{e.preventDefault();uploadZone.classList.remove('drag-over');addFiles(e.dataTransfer.files)}});
        fileInput.addEventListener('change',function(e){{addFiles(e.target.files);fileInput.value=''}});

        function addFiles(newFiles){{var added=0;for(var i=0;i<newFiles.length;i++){{var f=newFiles[i];if(!f.type.match(/^image\\/(png|jpeg|webp)$/))continue;if(f.size>25*1024*1024){{showToast(f.name+' is too large (>25MB)');continue}}if(files.length>=20){{showToast('Max 20 files');break}}var dup=false;for(var j=0;j<files.length;j++){{if(files[j].name===f.name&&files[j].size===f.size){{dup=true;break}}}}if(!dup){{files.push(f);added++}}}}if(added>0){{renderBatchList();showFile(0);controls.style.display='block';controls.scrollIntoView({{behavior:'smooth'}})}}}}

        function renderBatchList(){{batchList.innerHTML='';fileCount.textContent=files.length+' file'+(files.length>1?'s':'');for(var i=0;i<files.length;i++){{var chip=document.createElement('span');chip.className='batch-chip'+(i===currentFileIdx?' active':'');chip.innerHTML='<span>'+files[i].name+'</span><span class=\"remove\" data-idx=\"'+i+'\">×</span>';chip.addEventListener('click',function(idx){{return function(e){{if(e.target.className==='remove'){{removeFile(idx);return}}showFile(idx)}}}}(i));batchList.appendChild(chip)}}downloadAllBtn.style.display=files.length>1?'inline-flex':'none'}}

        function removeFile(idx){{files.splice(idx,1);compressedResults=[];if(files.length===0){{controls.style.display='none';batchList.innerHTML='';fileCount.textContent='';downloadAllBtn.style.display='none';return}}if(currentFileIdx>=files.length)currentFileIdx=files.length-1;renderBatchList();showFile(currentFileIdx)}}

        function showFile(idx){{currentFileIdx=idx;var f=files[idx];var r=new FileReader();r.onload=function(e){{previewImage.src=e.target.result}};r.readAsDataURL(f);originalInfo.textContent=formatSize(f.size)+' — '+f.type.replace('image/','').toUpperCase()+' — '+'';compressedPreview.innerHTML='<p style=\"color:#94A3B8;font-size:.9rem\">Adjust settings and click Compress</p>';compressedInfo.textContent='';compressionStats.style.display='none';downloadBtn.disabled=true;renderBatchList();loadImageDimensions(f)}}

        function loadImageDimensions(f){{var img=new Image();img.onload=function(){{originalInfo.textContent=formatSize(f.size)+' — '+f.type.replace('image/','').toUpperCase()+' — '+img.width+'×'+img.height}};img.src=URL.createObjectURL(f)}}

        modeQuality.addEventListener('click',function(){{currentMode='quality';modeQuality.classList.add('active');modeTarget.classList.remove('active');qualityGroup.style.display='flex';targetGroup.style.display='none'}});
        modeTarget.addEventListener('click',function(){{currentMode='target';modeTarget.classList.add('active');modeQuality.classList.remove('active');qualityGroup.style.display='none';targetGroup.style.display='flex'}});

        qualitySlider.addEventListener('input',function(){{qualityValue.textContent=qualitySlider.value+'%'}});

        if(presetTarget){{currentMode='target';modeTarget.classList.add('active');modeQuality.classList.remove('active');qualityGroup.style.display='none';targetGroup.style.display='flex';targetSizeInput.value=presetTarget}}

        compressBtn.addEventListener('click',function(){{if(!files.length)return;compressBtn.textContent='Compressing...';compressBtn.disabled=true;progressBar.style.display='block';progressFill.style.width='0%';compressedResults=[];processNext()}});

        function processNext(){{if(currentFileIdx>=files.length){{compressBtn.textContent='Compress All';compressBtn.disabled=false;progressBar.style.display='none';downloadAllBtn.disabled=false;return}}var f=files[currentFileIdx];var quality=parseInt(qualitySlider.value)/100;var outFormat=formatSelect.value;if(currentMode==='target'){{compressToTarget(f,outFormat,function(blob){{finishFile(blob);processNext()}});return}}compressWithQuality(f,quality,outFormat,function(blob){{finishFile(blob);processNext()}})}}

        function finishFile(blob){{compressedResults[currentFileIdx]=blob;progressFill.style.width=((currentFileIdx+1)/files.length*100)+'%';currentFileIdx++;showFile(Math.min(currentFileIdx,files.length-1))}}

        function compressWithQuality(file,quality,outFormat,cb){{var r=new FileReader();r.onload=function(e){{var img=new Image();img.onload=function(){{var c=document.createElement('canvas');c.width=img.width;c.height=img.height;var ctx=c.getContext('2d');ctx.drawImage(img,0,0);var mime=outFormat==='keep'?file.type:outFormat;c.toBlob(function(blob){{cb(blob)}},mime,quality)}};img.src=e.target.result}};r.readAsDataURL(file)}}

        function compressToTarget(file,outFormat,cb){{var targetKB=parseFloat(targetSizeInput.value)||100;var targetBytes=targetKB*1024;var mime=outFormat==='keep'?file.type:outFormat;var r=new FileReader();r.onload=function(e){{var img=new Image();img.onload=function(){{var lo=0.01,hi=1.0,mid,best=null,bestBlob=null;function tryQ(){{if(lo>hi){{cb(bestBlob);return}}mid=(lo+hi)/2;var c=document.createElement('canvas');c.width=img.width;c.height=img.height;var ctx=c.getContext('2d');ctx.drawImage(img,0,0);c.toBlob(function(blob){{if(!best||Math.abs(blob.size-targetBytes)<Math.abs(best.size-targetBytes)){{best=blob;bestBlob=blob}}if(blob.size>targetBytes){{hi=mid-0.02}}else{{lo=mid+0.02}}if(lo>hi||Math.abs(blob.size-targetBytes)/targetBytes<0.05){{cb(bestBlob);return}}tryQ()}},mime,mid)}}tryQ()}};img.src=e.target.result}};r.readAsDataURL(file)}}

        function updatePreview(blob){{var url=URL.createObjectURL(blob);compressedPreview.innerHTML='<img src=\"'+url+'\" alt=\"Compressed preview\" style=\"max-width:100%;max-height:260px;border-radius:8px;object-fit:contain\">';compressedInfo.textContent=formatSize(blob.size)+' — '+blob.type.replace('image/','').toUpperCase()}}

        downloadBtn.addEventListener('click',function(){{if(!compressedResults[currentFileIdx]){{compressCurrentThenDownload();return}}downloadBlob(compressedResults[currentFileIdx],files[currentFileIdx].name)}});

        function compressCurrentThenDownload(){{var f=files[currentFileIdx];var quality=parseInt(qualitySlider.value)/100;var outFormat=formatSelect.value;if(currentMode==='target'){{compressToTarget(f,outFormat,function(blob){{compressedResults[currentFileIdx]=blob;updatePreview(blob);downloadBlob(blob,f.name)}})}}else{{compressWithQuality(f,quality,outFormat,function(blob){{compressedResults[currentFileIdx]=blob;updatePreview(blob);downloadBlob(blob,f.name)}})}}}}

        function downloadBlob(blob,origName){{var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;var base=origName.replace(/\\.[^.]+$/,'');var ext=blob.type.split('/')[1]||'jpg';a.download=base+'-compressed.'+ext;document.body.appendChild(a);a.click();document.body.removeChild(a);URL.revokeObjectURL(url)}}

        downloadAllBtn.addEventListener('click',function(){{if(compressedResults.length===0)return;if(files.length===1&&compressedResults[0]){{downloadBlob(compressedResults[0],files[0].name);return}}var zip=new JSZip();var count=0;for(var i=0;i<files.length;i++){{if(compressedResults[i]){{var ext=compressedResults[i].type.split('/')[1]||'jpg';var name=files[i].name.replace(/\\.[^.]+$/,'')+'-compressed.'+ext;zip.file(name,compressedResults[i]);count++}}}}if(count===0){{showToast('Please compress files first');return}}zip.generateAsync({{type:'blob'}}).then(function(b){{downloadBlob(b,'compressed-images.zip')}}).catch(function(){{showToast('Failed to create ZIP')}})}});

        document.getElementById('toast').addEventListener('click',function(){{this.classList.remove('show')}});
    }})();
    </script>"""

def _img_tool_html(preset_target_kb=""):
    t = preset_target_kb
    return f"""<section class="tool-area" id="tool">
        <div class="batch-list" id="batchList"></div>
        <p class="file-count" id="fileCount"></p>
        <div class="upload-zone" id="uploadZone">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <p class="upload-zone__text">Drop images here, or <span style="color:#4F46E5;font-weight:600">click to browse</span></p>
            <p class="upload-zone__formats">PNG, JPEG, WebP — Up to 20 files, 25MB each</p>
            <input type="file" id="fileInput" accept="image/png,image/jpeg,image/webp" multiple hidden>
        </div>
        <div class="progress-bar" id="progressBar"><div class="fill" id="progressFill"></div></div>
        <div id="controls" style="display:none">
            <div class="preview-row">
                <div class="preview-card"><h3>Original</h3><img id="previewImage" alt="Original"><p class="file-info" id="originalInfo"></p></div>
                <div class="preview-card"><h3>Compressed</h3><div id="compressedPreview" style="min-height:100px;display:flex;align-items:center;justify-content:center;color:#94A3B8;font-size:.9rem">Adjust settings and click Compress</div><p class="file-info" id="compressedInfo"></p></div>
            </div>
            <div class="control-row">
                <div class="mode-toggle">
                    <button class="active" id="modeQuality">Quality</button>
                    <button id="modeTarget">Target Size</button>
                </div>
                <div class="quality-control" id="qualityGroup">
                    <label>Quality: <span id="qualityValue">80%</span></label>
                    <input type="range" id="qualitySlider" min="10" max="100" value="80" step="1">
                </div>
                <div class="target-input" id="targetGroup" style="display:none">
                    <span>Target:</span>
                    <input type="number" id="targetSizeInput" value="{t}" min="1" max="25000" step="1">
                    <span>KB</span>
                </div>
                <div class="format-select">
                    <select id="formatSelect">
                        <option value="keep">Keep Original Format</option>
                        <option value="image/jpeg">JPEG</option>
                        <option value="image/png">PNG</option>
                        <option value="image/webp">WebP</option>
                    </select>
                </div>
            </div>
            <div class="compression-stats" id="compressionStats" style="display:none">
                <div class="stat"><span class="stat__label">Original</span><span class="stat__value" id="origSize">—</span></div>
                <div class="stat"><span class="stat__label">Compressed</span><span class="stat__value" id="compSize">—</span></div>
                <div class="stat"><span class="stat__label">Saved</span><span class="stat__value stat__value--highlight" id="savedPercent">—</span></div>
            </div>
            <div class="btn-row">
                <button class="btn btn-primary" id="compressBtn">Compress</button>
                <button class="btn btn-success" id="downloadBtn" disabled>Download</button>
                <button class="btn btn-outline" id="downloadAllBtn" style="display:none">Download All (ZIP)</button>
            </div>
        </div>
        <div class="ad-slot"><div class="ad-placeholder">Advertisement</div></div>
    </section>"""

def _build_scene_page(scene, replacements, all_scenes, template_type="generic"):
    """Build HTML for one scene-targeted sub-page with FAQ Schema and internal links.

    For image-compress template_type, embeds the interactive image compression tool.
    Other template types use a generic textarea-based tool placeholder.
    """
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

    # Detect target size from slug (e.g. "compress-image-to-20kb" → "20")
    import re
    target_kb = ""
    m = re.search(r'to-(\d+)kb', scene.get("slug", ""))
    if m:
        target_kb = m.group(1)

    is_image_tool = (template_type == "image-compress")

    if is_image_tool:
        tool_css = _img_tool_css()
        tool_html_block = _img_tool_html(target_kb)
        tool_js = _img_tool_js(target_kb)
        body_steps = f"""<h2>About {esc_scenario}</h2>
            <p>This tool helps you {esc_scenario.lower()}. {esc_tool_desc} No downloads or installations required — everything runs directly in your browser.</p>
            <h2>How to {esc_scenario}</h2>
            <p>Step 1: Drop your image into the upload zone above.</p>
            <p>Step 2: Choose your compression settings — adjust quality or set a target file size.</p>
            <p>Step 3: Click "Compress" and download the result. Done.</p>
            <h2>Why Use This Tool?</h2>
            <p>Unlike desktop software, there is nothing to install. Unlike other online tools, we do not require signup. Unlike mobile apps, this works on any device with a browser. And unlike paid alternatives, it is completely free. All compression happens locally — your files never leave your device.</p>"""
    else:
        tool_css = ""
        tool_html_block = f"""<section class="tool-area">
            <textarea id="toolInput" placeholder="Paste or upload your content here..."></textarea>
            <div class="output-area" id="toolOutput"></div>
            <p class="error-msg" id="errorMsg"></p>
            <div class="btn-row">
                <button class="btn btn-primary" id="actionBtn">Process Now</button>
                <button class="btn btn-secondary" id="clearBtn">Clear</button>
                <button class="btn btn-secondary" id="copyBtn">Copy Result</button>
            </div>
            <div class="ad-slot"><div class="ad-placeholder">Advertisement</div></div>
        </section>"""
        tool_js = """<script>
            const input=document.getElementById('toolInput');const output=document.getElementById('toolOutput');const errorMsg=document.getElementById('errorMsg');
            document.getElementById('actionBtn').addEventListener('click',()=>{const v=input.value.trim();if(!v){errorMsg.textContent='Please enter some input.';errorMsg.style.display='block';output.style.display='none';return}errorMsg.style.display='none';output.textContent=v;output.style.display='block'});
            document.getElementById('clearBtn').addEventListener('click',()=>{input.value='';output.style.display='none';errorMsg.style.display='none'});
            document.getElementById('copyBtn').addEventListener('click',()=>{if(!output.textContent)return;navigator.clipboard.writeText(output.textContent).then(()=>{const b=document.getElementById('copyBtn');b.textContent='Copied!';setTimeout(()=>b.textContent='Copy Result',1500)})});
        </script>"""
        body_steps = f"""<h2>About {esc_scenario}</h2>
            <p>This tool helps you {esc_scenario.lower()}. {esc_tool_desc} No downloads or installations required — everything runs directly in your browser.</p>
            <h2>How to {esc_scenario}</h2>
            <p>Step 1: Upload or paste your content into the tool above.</p>
            <p>Step 2: Click "Process Now" and wait a few seconds.</p>
            <p>Step 3: Copy or download the result. Done.</p>
            <h2>Why Use This Tool?</h2>
            <p>Unlike desktop software, there is nothing to install. Unlike other online tools, we do not require signup. Unlike mobile apps, this works on any device with a browser. And unlike paid alternatives, it is completely free.</p>"""

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
        {tool_css}
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
                <a href="#tool">Try It</a>
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
        {tool_html_block}
        <section class="scene-body">
            {body_steps}
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
    <div class="toast" id="toast"></div>
    {tool_js}
</body>
</html>"""