"""
sitegen.py - regenerates every page on the site from comic/chapters.json.

Pages are written as plain static HTML with the image tags baked in: no
client-side fetching, so the site works when opened straight from disk,
works with JavaScript off, and is readable by search engines.
"""
from __future__ import annotations
import html, json
from pathlib import Path

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="{root}assets/css/site.css">
</head>
<body class="{cls}">
"""

def nav(root, here=""):
    def a(href, label, key):
        cur = ' aria-current="page"' if key == here else ""
        return f'<a href="{root}{href}"{cur}>{label}</a>'
    return (f'<nav class="sitenav"><a class="wordmark" href="{root}index.html">Featherweight</a>'
            f'<span class="navlinks">{a("chapters.html","Chapters","chapters")}'
            f'{a("about.html","About","about")}</span></nav>')

def foot(root):
    return ('<footer class="sitefoot"><p>Featherweight &middot; '
            'made by Meg</p></footer>\n</body>\n</html>\n')

def e(s):
    return html.escape(str(s or ""), quote=True)

def pub_chapters(m):
    return sorted([c for c in m["chapters"] if c.get("status") == "published"],
                  key=lambda c: c["number"])

def fmt_date(d):
    try:
        y, mo, da = d.split("-")
        months = ["January","February","March","April","May","June","July",
                  "August","September","October","November","December"]
        return f"{int(da)} {months[int(mo)-1]} {y}"
    except Exception:
        return d or ""

# ------------------------------------------------------------------ home
def home(m):
    site, chs = m["site"], pub_chapters(m)
    first, latest = (chs[0], chs[-1]) if chs else (None, None)
    p = [HEAD.format(title=e(site["title"]), desc=e(site.get("tagline","")),
                     root="", cls="page")]
    p.append(nav("", "home"))
    p.append('<main class="wrap">')
    p.append('<section class="hero">')
    p.append(f'<h1>{e(site["title"])}</h1>')
    if site.get("tagline"):
        p.append(f'<p class="tagline">{e(site["tagline"])}</p>')
    if first:
        p.append(f'<a class="btn" href="read/{first["id"]}/">Start reading</a>')
    p.append('</section>')

    if latest:
        p.append('<section class="latest"><h2 class="lede">Latest chapter</h2>')
        p.append(f'<a class="chapcard wide" href="read/{latest["id"]}/">')
        p.append(f'<img src="comic/{latest["id"]}/{latest["cover"]}" alt="" '
                 f'width="400" height="500" loading="lazy">')
        p.append('<div class="chapmeta">'
                 f'<span class="num">Chapter {latest["number"]}</span>'
                 f'<span class="ctitle">{e(latest["title"])}</span>'
                 f'<span class="date">{fmt_date(latest.get("published"))}</span>'
                 '</div></a></section>')

    if len(chs) > 1:
        p.append('<section class="recent"><h2 class="lede">Recent</h2><ul class="chaplist">')
        for c in reversed(chs[:-1][-3:]):
            p.append(f'<li><a href="read/{c["id"]}/"><b>Chapter {c["number"]}</b>'
                     f'<span>{e(c["title"])}</span>'
                     f'<time>{fmt_date(c.get("published"))}</time></a></li>')
        p.append('</ul></section>')

    p.append(f'<p class="allink"><a href="chapters.html">All chapters &rarr;</a></p>')
    p.append('</main>')
    p.append(foot(""))
    return "\n".join(p)

# -------------------------------------------------------------- chapters
def chapters_page(m):
    chs = pub_chapters(m)
    p = [HEAD.format(title=f'Chapters &middot; {e(m["site"]["title"])}',
                     desc="Every chapter of Featherweight.", root="", cls="page")]
    p.append(nav("", "chapters"))
    p.append('<main class="wrap">')
    p.append('<h1 class="pagetitle">Chapters</h1>')
    if not chs:
        p.append('<p class="empty">No chapters published yet.</p>')
    else:
        p.append('<div class="chapgrid">')
        for c in chs:
            p.append(f'<a class="chapcard" href="read/{c["id"]}/">')
            p.append(f'<img src="comic/{c["id"]}/{c["cover"]}" alt="" '
                     f'width="400" height="500" loading="lazy">')
            p.append('<div class="chapmeta">'
                     f'<span class="num">Chapter {c["number"]}</span>'
                     f'<span class="ctitle">{e(c["title"])}</span>'
                     f'<span class="date">{fmt_date(c.get("published"))}</span>'
                     '</div></a>')
        p.append('</div>')
    p.append('</main>')
    p.append(foot(""))
    return "\n".join(p)

# ---------------------------------------------------------------- reader
def reader(root_dir: Path, m, ch):
    chs = pub_chapters(m)
    ids = [c["id"] for c in chs]
    i = ids.index(ch["id"]) if ch["id"] in ids else -1
    prev = chs[i-1] if i > 0 else None
    nxt = chs[i+1] if 0 <= i < len(chs)-1 else None

    cdir = root_dir / "comic" / ch["id"]
    img_base = f'../../comic/{ch["id"]}/'

    notes_file = cdir / "notes.html"
    notes = ""
    if notes_file.exists():
        raw = notes_file.read_text(encoding="utf-8")
        stripped = "\n".join(l for l in raw.splitlines()
                             if not l.strip().startswith("<!--")).strip()
        if stripped and "-->" not in stripped:
            notes = raw
        else:
            body = raw.split("-->", 1)[-1].strip()
            notes = body
    extras = sorted([q.name for q in (cdir / "extras").glob("*.webp")]) \
        if (cdir / "extras").is_dir() else []

    title = f'Chapter {ch["number"]}: {e(ch["title"])} &middot; {e(m["site"]["title"])}'
    p = [HEAD.format(title=title, desc=e(ch["title"]), root="../../", cls="reader")]
    p.append('<div class="progress"><div class="progress-bar" id="pbar"></div></div>')
    p.append('<header class="readerbar" id="readerbar">')
    p.append('<a class="back" href="../../chapters.html">&larr; Chapters</a>')
    p.append(f'<span class="rtitle">Ch. {ch["number"]} &mdash; {e(ch["title"])}</span>')
    p.append('<button class="helpbtn" id="helpbtn" aria-label="Keyboard shortcuts" '
             'title="Keyboard shortcuts">?</button>')
    p.append('</header>')

    p.append('<main>')
    p.append(f'<div class="strip" id="strip" style="--strip-w:{ch["width"]}px">')
    for n, s in enumerate(ch["slices"]):
        eager = n < 2
        alt = e(f'{m["site"]["title"]}, chapter {ch["number"]}: {ch["title"]}') if n == 0 else ""
        p.append(
            f'<img src="{img_base}{s["file"]}" width="{ch["width"]}" height="{s["h"]}" '
            f'alt="{alt}" decoding="async" '
            + ('fetchpriority="high">' if eager else 'loading="lazy">'))
    p.append('</div>')

    p.append('<section class="chapterend">')
    p.append(f'<p class="endmark">End of Chapter {ch["number"]}</p>')
    if notes.strip():
        p.append('<div class="notes"><h2 class="lede">Notes</h2>'
                 f'<div class="notesbody">{notes}</div></div>')
    if extras:
        p.append('<div class="extras"><h2 class="lede">Extras</h2><div class="extragrid">')
        for x in extras:
            p.append(f'<img src="{img_base}extras/{x}" alt="" loading="lazy">')
        p.append('</div></div>')
    p.append('<!-- comments slot: a Giscus script tag drops in here -->')
    p.append('<nav class="chnav">')
    p.append(f'<a class="cn prev" href="../{prev["id"]}/">&larr; Ch. {prev["number"]}</a>'
             if prev else '<span class="cn ghost"></span>')
    p.append('<a class="cn mid" href="../../chapters.html">All chapters</a>')
    p.append(f'<a class="cn next" href="../{nxt["id"]}/">Ch. {nxt["number"]} &rarr;</a>'
             if nxt else '<span class="cn ghost"></span>')
    p.append('</nav>')
    p.append('</section>')
    p.append('</main>')

    p.append('<div class="resume" id="resume" hidden>'
             '<span>You were partway through this chapter.</span>'
             '<button id="resumego">Jump back</button>'
             '<button id="resumeno" class="quiet">Start over</button></div>')
    p.append('<div class="helppanel" id="helppanel" hidden><h3>Shortcuts</h3><dl>'
             '<dt><kbd>J</kbd> <kbd>&darr;</kbd></dt><dd>Down</dd>'
             '<dt><kbd>K</kbd> <kbd>&uarr;</kbd></dt><dd>Up</dd>'
             '<dt><kbd>[</kbd> <kbd>]</kbd></dt><dd>Prev / next chapter</dd>'
             '<dt><kbd>C</kbd></dt><dd>Chapter list</dd>'
             '<dt><kbd>Home</kbd> <kbd>End</kbd></dt><dd>Start / end</dd>'
             '<dt><kbd>?</kbd></dt><dd>This panel</dd>'
             '</dl><button id="helpclose">Close</button></div>')

    p.append(f'<script src="../../assets/js/reader.js" data-chapter="{ch["id"]}" '
             f'data-prev="{prev["id"] + "/" if prev else ""}" '
             f'data-next="{nxt["id"] + "/" if nxt else ""}"></script>')
    p.append('</body>\n</html>')
    return "\n".join(p)

# ------------------------------------------------------------------ main
def build_site(root: Path, m: dict):
    (root / "index.html").write_text(home(m), encoding="utf-8")
    (root / "chapters.html").write_text(chapters_page(m), encoding="utf-8")
    for ch in m["chapters"]:
        d = root / "read" / ch["id"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(reader(root, m, ch), encoding="utf-8")
        print(f"      read/{ch['id']}/index.html  ({len(ch['slices'])} slices)")
    print("      index.html, chapters.html")
