#!/usr/bin/env python3
"""
build_chapter.py - slice vertical-scroll comic strips into web-ready WebP,
then regenerate every page on the site from the manifest.

  python3 tools/build_chapter.py ch01 --title "Chapter title"
  python3 tools/build_chapter.py ch01 --title "..." --quality 92 --status draft
  python3 tools/build_chapter.py --regen        # rebuild pages only, no slicing

Source strips go in  source/<id>/  named so they sort in reading order
(01.png, 02.png, ...). Any heights are fine - they are stitched into one
continuous strip before cutting, so the joins never land on a slice edge.
"""
from __future__ import annotations
import argparse, io, json, re, sys, datetime
from pathlib import Path
from PIL import Image, ImageCms

ROOT     = Path(__file__).resolve().parent.parent
COMIC    = ROOT / "comic"
SOURCE   = ROOT / "source"
MANIFEST = COMIC / "chapters.json"

Image.MAX_IMAGE_PIXELS = None
SRGB = ImageCms.createProfile("sRGB")

DEFAULT_SLICE_H = 2000
DEFAULT_QUALITY = 88

def log(m=""): print(m, flush=True)

def natural_key(p: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]

# ---------------------------------------------------------------- manifest
def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {
        "site": {
            "title": "Featherweight",
            "tagline": "A vertical-scroll comic.",
            "author": "Meg",
            "description": "",
        },
        "chapters": [],
    }

def save_manifest(m: dict):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")

# ---------------------------------------------------------------- imaging
def prepare(im: Image.Image) -> Image.Image:
    """Flatten any transparency onto white, then convert to sRGB."""
    icc = im.info.get("icc_profile")
    if im.mode in ("RGBA", "LA", "P"):
        rgba = im.convert("RGBA")
        alpha = rgba.getchannel("A")
        if alpha.getextrema()[0] < 255:
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=alpha)
            out = bg
        else:
            out = rgba.convert("RGB")
    else:
        out = im.convert("RGB")
    if icc:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            if "srgb" in ImageCms.getProfileDescription(src).strip().lower():
                return out          # already sRGB — nothing to convert

            out = ImageCms.profileToProfile(out, src, SRGB, outputMode="RGB")
        except Exception as e:
            log(f"      ! colour conversion skipped ({e}); treating as sRGB")
    return out

class Strips:
    """Presents several source files as one continuous strip, loading lazily."""
    def __init__(self, paths):
        self.paths, self.heights, self.widths, self.offsets = paths, [], [], []
        for p in paths:
            with Image.open(p) as im:
                self.widths.append(im.width)
                self.heights.append(im.height)
        t = 0
        for h in self.heights:
            self.offsets.append(t); t += h
        self.total = t
        self.width = self.widths[0]
        self._i, self._im = None, None

    def _load(self, i):
        if self._i != i:
            self._im = None
            log(f"      reading {self.paths[i].name} "
                f"({self.widths[i]}x{self.heights[i]})")
            with Image.open(self.paths[i]) as raw:
                self._im = prepare(raw)
            self._i = i
        return self._im

    def window(self, y0, y1) -> Image.Image:
        out = Image.new("RGB", (self.width, y1 - y0), (255, 255, 255))
        for i, (off, h) in enumerate(zip(self.offsets, self.heights)):
            a, b = max(y0, off), min(y1, off + h)
            if b <= a:
                continue
            w = min(self.width, self.widths[i])
            out.paste(self._load(i).crop((0, a - off, w, b - off)), (0, a - y0))
        return out

# ---------------------------------------------------------------- build
def build_chapter(cid, title, number, quality, slice_h, status, published):
    src_dir = SOURCE / cid
    if not src_dir.is_dir():
        sys.exit(f"No source folder: source/{cid}/")
    paths = sorted(
        [p for p in src_dir.iterdir()
         if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")],
        key=natural_key)
    if not paths:
        sys.exit(f"No images in source/{cid}/")

    log(f"  {cid}: {len(paths)} source file(s)")
    strips = Strips(paths)
    if len(set(strips.widths)) > 1:
        log(f"      ! widths differ: {strips.widths} - using {strips.width}px, "
            f"narrower strips will be padded white")
    log(f"      continuous strip: {strips.width} x {strips.total}px")

    out_dir = COMIC / cid
    out_dir.mkdir(parents=True, exist_ok=True)

    # cover: top of the chapter, cropped 4:5
    cov_h = min(int(strips.width * 1.25), strips.total)
    cover = strips.window(0, cov_h).resize((400, int(400 * cov_h / strips.width)), Image.LANCZOS)
    cover.save(out_dir / "cover.webp", "WEBP", quality=82, method=5)

    slices, total_bytes, n = [], 0, 0
    y = 0
    while y < strips.total:
        y2 = min(y + slice_h, strips.total)
        n += 1
        name = f"{n:03d}.webp"
        img = strips.window(y, y2)
        img.save(out_dir / name, "WEBP", quality=quality, method=5)
        size = (out_dir / name).stat().st_size
        total_bytes += size
        slices.append({"file": name, "h": y2 - y})
        y = y2
    log(f"      {n} slices, {total_bytes/1048576:.2f} MB total "
        f"(avg {total_bytes/n/1024:.0f} KB) at quality {quality}")

    # remove orphaned slices from an earlier, longer build
    for p in sorted(out_dir.glob("[0-9][0-9][0-9].webp")):
        if int(p.stem) > n:
            try:
                p.unlink(); log(f"      removed stale {p.name}")
            except OSError:
                log(f"      ! could not remove stale {p.name} (delete not permitted)")

    notes = out_dir / "notes.html"
    if not notes.exists():
        notes.write_text(
            "<!-- Your end-of-chapter notes. Plain HTML: <p>, <b>, <i>, <a>, <img>.\n"
            "     Delete everything below to hide this section.\n"
            "     This file is created once and is never overwritten by a rebuild. -->\n"
            "<p>Thanks for reading.</p>\n", encoding="utf-8")
        log("      created notes.html (yours - never overwritten)")
    (out_dir / "extras").mkdir(exist_ok=True)

    chapter = {
        "id": cid, "number": number, "title": title,
        "published": published, "status": status, "cover": "cover.webp",
        "width": strips.width, "totalHeight": strips.total,
        "quality": quality, "slices": slices,
    }
    (out_dir / "chapter.json").write_text(json.dumps(chapter, indent=2) + "\n", encoding="utf-8")
    return chapter

# ---------------------------------------------------------------- cli
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter", nargs="?", help="chapter id, e.g. ch02")
    ap.add_argument("--title", default=None)
    ap.add_argument("--number", type=int, default=None)
    ap.add_argument("--quality", type=int, default=DEFAULT_QUALITY)
    ap.add_argument("--slice-height", type=int, default=DEFAULT_SLICE_H)
    ap.add_argument("--status", choices=["published", "draft"], default="published")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--regen", action="store_true", help="rebuild pages only")
    a = ap.parse_args()

    sys.path.insert(0, str(ROOT / "tools"))
    import sitegen

    m = load_manifest()

    if not a.regen:
        if not a.chapter:
            ap.error("give a chapter id, or --regen")
        cid = a.chapter
        existing = next((c for c in m["chapters"] if c["id"] == cid), None)
        number = a.number or (existing["number"] if existing
                              else max([c["number"] for c in m["chapters"]] or [0]) + 1)
        title = a.title or (existing["title"] if existing else f"Chapter {number}")
        published = a.date or (existing["published"] if existing
                               else datetime.date.today().isoformat())
        log(f"Building {cid} - \"{title}\"")
        ch = build_chapter(cid, title, number, a.quality, a.slice_height, a.status, published)
        m["chapters"] = [c for c in m["chapters"] if c["id"] != cid] + [ch]
        m["chapters"].sort(key=lambda c: c["number"])
        save_manifest(m)

    log("Regenerating pages...")
    sitegen.build_site(ROOT, m)
    pub = [c for c in m["chapters"] if c["status"] == "published"]
    log(f"Done. {len(pub)} published chapter(s), {len(m['chapters'])} total.")

if __name__ == "__main__":
    main()
