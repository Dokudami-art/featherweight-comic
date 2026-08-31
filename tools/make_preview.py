#!/usr/bin/env python3
"""
make_preview.py - package the real site into ONE self-contained HTML file
so it can be previewed before anything is pushed to GitHub.

This does not rebuild or re-design anything: it reads the actual generated
pages, the actual stylesheet and the actual reader script, and inlines them.
What you see is what the site does. The only difference is that images are
downscaled to keep the file small, so judge layout and behaviour here and
judge image quality from the real files.

  python3 tools/make_preview.py [--width 1200] [--quality 82] [-o preview.html]
"""
import argparse, base64, io, re, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
Image.MAX_IMAGE_PIXELS = None

def body_of(p: Path):
    s = p.read_text(encoding="utf-8")
    m = re.search(r"<body[^>]*class=\"([^\"]*)\"[^>]*>(.*)</body>", s, re.S)
    if not m:
        sys.exit(f"could not find <body> in {p}")
    return m.group(1).strip(), m.group(2)

def data_uri(path: Path, width: int, quality: int, cache={}):
    key = (str(path), width, quality)
    if key in cache:
        return cache[key]
    im = Image.open(path)
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=quality, method=4)
    uri = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    cache[key] = uri
    return uri

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("-o", "--out", default=str(ROOT / "preview.html"))
    a = ap.parse_args()

    pages = {
        "home":     ROOT / "index.html",
        "chapters": ROOT / "chapters.html",
        "about":    ROOT / "about.html",
        "ch01":     ROOT / "read" / "ch01" / "index.html",
    }

    # ---- link rewrites: every internal href becomes a router call ----
    LINKS = [
        (r'href="(?:\.\./)*index\.html"',     'href="#" data-go="home"'),
        (r'href="(?:\.\./)*chapters\.html"',  'href="#" data-go="chapters"'),
        (r'href="(?:\.\./)*about\.html"',     'href="#" data-go="about"'),
        (r'href="(?:\.\./)*read/ch01/"',      'href="#" data-go="ch01"'),
        (r'href="\.\./ch01/"',                'href="#" data-go="ch01"'),
    ]

    blocks, total_imgs, unresolved = [], 0, []
    for key, path in pages.items():
        cls, html = body_of(path)
        for pat, rep in LINKS:
            html = re.sub(pat, rep, html)
        html = re.sub(r'<script\s+src="[^"]*\.js"[^>]*>\s*</script>', '', html, flags=re.S)

        def swap(m):
            nonlocal total_imgs
            src = m.group(1)
            rel = re.sub(r"^(\.\./)+", "", src)
            f = ROOT / rel
            if not f.exists():
                unresolved.append(src)
                return m.group(0)
            total_imgs += 1
            return m.group(0).replace(src, data_uri(f, a.width, a.quality))
        html = re.sub(r'src="([^"]+\.(?:webp|png|jpe?g|gif|svg))"', swap, html)
        blocks.append(f'<div class="pv-page" id="pv-{key}" data-bodyclass="{cls}" hidden>{html}</div>')
        print(f"  packaged {key:9s} ({path.relative_to(ROOT)})")

    css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")
    chapters_js = (ROOT / "assets/js/chapters.js").read_text(encoding="utf-8")
    theme_js    = (ROOT / "assets/js/theme.js").read_text(encoding="utf-8")

    # ---- the real reader script, with navigation pointed at the router ----
    js = (ROOT / "assets/js/reader.js").read_text(encoding="utf-8")
    subs = [
        ('var tag  = document.currentScript;',
         'var tag  = { dataset: { chapter: "ch01", prev: "", next: "" } };'),
        ('function go(where) { if (where) location.href = "../" + where; }',
         'function go(where) { if (where) window.__pv(where.replace("/", "")); }'),
        ('case "c": case "C": location.href = "../../chapters.html"; break;',
         'case "c": case "C": window.__pv("chapters"); break;'),
        ('(function () {\n  "use strict";', 'window.__initReader = function () {\n  "use strict";'),
        ('\n  onScroll();\n})();', '\n  onScroll();\n};'),
    ]
    for old, new in subs:
        if old not in js:
            sys.exit(f"reader.js changed - preview substitution failed on:\n{old}")
        js = js.replace(old, new, 1)

    out = f"""<title>Featherweight Preview</title>
<style>
{css}
/* ---- preview shell only: not part of the real site ---- */
.pv-page[hidden]{{display:none}}
:root[data-theme="dark"] .wordmark{{filter:invert(1)}}
:root[data-theme="light"] .wordmark{{filter:none}}
/* the artifact viewer stamps an explicit theme; map it onto the site's tokens */
:root[data-theme="dark"]{{
  --bg:#111317; --surface:#181b20; --ink:#e6e8ec; --muted:#949cab;
  --line:#282c33; --accent:#79aeea; --reader-bg:#0c0d10; --bar:rgba(17,19,23,.94);
}}
:root[data-theme="light"]{{
  --bg:#ffffff; --surface:#f5f5f6; --ink:#16181c; --muted:#6a7280;
  --line:#e2e4e8; --accent:#2f6db4; --reader-bg:#e8e9eb; --bar:rgba(255,255,255,.94);
}}
</style>

{chr(10).join(blocks)}

<script>
(function () {{
  var pages = ["home","chapters","about","ch01"], started = false;
  window.__pv = function (name) {{
    if (pages.indexOf(name) < 0) name = "home";
    pages.forEach(function (p) {{
      document.getElementById("pv-" + p).hidden = (p !== name);
    }});
    document.body.className = document.getElementById("pv-" + name).dataset.bodyclass;
    window.scrollTo(0, 0);
    if (name === "ch01" && !started) {{ started = true; window.__initReader(); }}
  }};
  document.addEventListener("click", function (ev) {{
    var a = ev.target.closest("a[data-go]");
    if (a) {{ ev.preventDefault(); window.__pv(a.dataset.go); }}
  }});
  window.__pv("home");
}})();
{js}
</script>
<script>
{chapters_js}
</script>
<script>
{theme_js}
</script>
"""
    leftover = re.findall(r'src="(?!data:)([^"]+)"', out)
    if unresolved or leftover:
        sys.exit("REFUSING TO WRITE - these images were not inlined and would "
                 "render as broken links:\n  " + "\n  ".join(sorted(set(unresolved + leftover))))
    Path(a.out).write_text(out, encoding="utf-8")
    mb = Path(a.out).stat().st_size / 1048576
    print(f"  {total_imgs} images inlined at {a.width}px q{a.quality}")
    print(f"  wrote {a.out}  ({mb:.2f} MB)")

if __name__ == "__main__":
    main()
