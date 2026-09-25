#!/usr/bin/env python3
"""build.py — static site generator.

What it does
------------
1. Reads the Pages CMS editable content: content/*.yml (one file per page
   section plus common.yml, footer.yml, clinic_info.yml and signature.yml)
   and the type registry .pages.yml.
2. Walks the templates src/index.html and src/signature.html substituting the
   __file.path.field__ markers (e.g. __hero.badge__, __services.items.0.title__
   or __common.contact.phone__) with the content of each file. The path is
   resolved in the YAML of the referenced file; the field type is read from
   .pages.yml and decides how it is rendered:
     - rich-text (Markdown)  -> converted to HTML
     - image                 -> normalized media/... path
     - component icon        -> icon HTML (ICONS)
     - list of strings       -> joined with <br>
     - everything else       -> escaped plain text
   If a marker is not found in the content or its field is not registered in
   .pages.yml, the build fails stating exactly which field was looked up and
   in which template.
3. Reads the domain from src/CNAME and fills the header of src/index.html from
   content/clinic_info.yml (read-only): <title>, description, keywords,
   canonical, geo tags, Open Graph and Twitter, language, logo and menu labels.
4. Generates the JSON-LD block (schema.org) announcing the clinic, the
   professional, the service catalog, the FAQ and the articles, with the data
   of clinic_info.yml and the other sections.
5. Writes the contact data of content/common.yml (single source of truth)
   straight into the generated index.html: the .neuro-* slots (phone,
   WhatsApp, email, address and Maps) are resolved without JavaScript.
6. Writes the full content of services, modalities and articles in the HTML
   itself (hidden .card-full blocks); script.js copies it into the modals.
7. Converts the media/ images that are still PNG or JPEG (photos uploaded from
   the CMS) to WebP and publishes only that version.
8. Copies the static files (CSS, JS, CNAME, favicon, logo and PDFs) into
   _site/, keeping the current public structure.

Usage
-----
    pip install pyyaml markdown pillow  # generator dependencies
    python scripts/build.py              # writes ./_site
    # Without pip (e.g. in an isolated environment):
    uv run --with pyyaml --with markdown --with pillow python scripts/build.py

GitHub Actions (.github/workflows/build_validation.yml on every PR and
.github/workflows/deploy_page.yml on push to main) does exactly this and
publishes _site/ to GitHub Pages. There is no framework and no site generator:
just this script.

Markers
-------
Format: __file.path.field__ (the first segment is the name of the file in
content/, e.g. __services.items.0.title__). Numeric segments walk lists. If
the file, the path or the field do not exist in content/*.yml, or the field is
not declared in .pages.yml, MissingFieldError is raised with the name of the
field that was looked up.

Repeated lists
--------------
Cards and list items (services, modalities, process steps, blog posts and FAQ
questions) are not written one by one in the index template: they are wrapped
in a template block that build.py repeats once per YAML element, so adding or
removing entries in the CMS requires no HTML change. See expand_loops() for
the syntax (@foreach).
"""

from __future__ import annotations

import html
import json
import re
import shutil
import struct
import sys
from fnmatch import fnmatch
from pathlib import Path

try:
    import markdown
    import yaml
except ImportError as exc:  # pragma: no cover
    missing = "Markdown" if exc.name == "markdown" else "PyYAML"
    sys.exit(f"Missing {missing}. Install it with:  pip install pyyaml markdown")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
CONTENT = ROOT / "content"
OUT = ROOT / "_site"

# Templates processed by build.py: (key for messages, path to the file).
# The .txt and .xml files are SEO/LLM templates: they also carry
# __file.path.field__ markers and are generated from the content/*.yml data.
TEMPLATES = {
    "src/index.html": SRC / "index.html",
    "src/signature.html": SRC / "signature.html",
    "src/robots.txt": SRC / "robots.txt",
    "src/sitemap.xml": SRC / "sitemap.xml",
    "src/llms.txt": SRC / "llms.txt",
    "src/llms-full.txt": SRC / "llms-full.txt",
}

# ---------------------------------------------------------------------------
# ICONS — single source of truth (keys = values of the "icon" field in
# .pages.yml). Each value is the HTML inserted in the card/modal.
# ---------------------------------------------------------------------------
SVG_ATTRS = (
    'xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"'
)


def svg(paths: str) -> str:
    return f"<svg {SVG_ATTRS}>{paths}</svg>"


ICONS: dict[str, str] = {
    # Inline SVG icons (they inherit size/color from the container)
    "brain": svg(
        '<path d="M12 18V5"/><path d="M15 13a4.17 4.17 0 0 1-3-4 4.17 4.17 0 0 1-3 4"/>'
        '<path d="M17.598 6.5A3 3 0 1 0 12 5a3 3 0 1 0-5.598 1.5"/>'
        '<path d="M17.997 5.125a4 4 0 0 1 2.526 5.77"/><path d="M18 18a4 4 0 0 0 2-7.464"/>'
        '<path d="M19.967 17.483A4 4 0 1 1 12 18a4 4 0 1 1-7.967-.517"/>'
        '<path d="M6 18a4 4 0 0 1-2-7.464"/><path d="M6.003 5.125a4 4 0 0 0-2.526 5.77"/>'
    ),
    "heart": svg(
        '<path d="M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5"/>'
        '<path d="M3.22 13H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27"/>'
    ),
    "zap": svg(
        '<path d="M15.914 4a1.5 1.5 0 0 0-2.474-1.561l-9 9A1.5 1.5 0 0 0 5.5 14h4.002a.5.5 0 0 1 .471.666L8.086 20a1.5 1.5 0 0 0 2.475 1.56l9-9A1.5 1.5 0 0 0 18.5 10h-3.997a.5.5 0 0 1-.472-.667z"/>'
    ),
    "message": svg('<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>'),
    "calendar": svg(
        '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>'
        '<path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>'
    ),
    "clipboard": svg(
        '<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/>'
        '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
        '<path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/>'
    ),
    "target": svg(
        '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/>'
        '<circle cx="12" cy="12" r="2"/>'
    ),
    "chart": svg(
        '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
        '<polyline points="16 7 22 7 22 13"/>'
    ),
    # Font icons from Bootstrap Icons (included in src/index.html)
    "building": '<i class="bi bi-building"></i>',
    "laptop": '<i class="bi bi-laptop"></i>',
    "house": '<i class="bi bi-house-door"></i>',
    "journal": '<i class="bi bi-journal-text"></i>',
}

# Static files copied into _site/. The resources that used to live in the root
# are now read from media/, but they are published in the root to keep the
# existing public paths (favicon, PDFs and logo).
STATIC_FILES = [
    (SRC / "styles.css", "styles.css"),
    (SRC / "script.js", "script.js"),
    (SRC / "CNAME", "CNAME"),
    (ROOT / "media/favicon.svg", "favicon.svg"),
    (ROOT / "media/logo.svg", "logo.svg"),
    (ROOT / "media/aviso_legal.pdf", "aviso_legal.pdf"),
    (ROOT / "media/tarjeta.pdf", "tarjeta.pdf"),
]
MEDIA_EXCLUDES = ("favicon.svg", "logo.svg", "aviso_legal.pdf", "tarjeta.pdf")

# Formats the build converts to WebP when publishing: the originals are not
# published, so every image of the site ends up in WebP.
RASTER_FORMATS = (".png", ".jpg", ".jpeg")

# Images published as they are even when they are PNG: image.png is the
# og:image that WhatsApp, Facebook and other social networks read when the
# link is shared, and some of them do not support WebP.
KEEP_AS_IS = ("image.png",)

# Images already converted in this build: path of the original (as written by
# media_url) -> (path of the published WebP, (width, height)). Filled by
# prepare_media() before the templates are rendered.
WEBP_SUBSTITUTES: dict[str, tuple[str, tuple[int, int]]] = {}

# Non-fatal warnings (e.g. modality photos not uploaded yet).
WARNINGS: list[str] = []

# Loaded content/*.yml, used by the renderers and by the structured data.
CONTEXT: dict = {}


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def esc(value) -> str:
    """Escapes plain text to be inserted in HTML (not for Markdown)."""
    return html.escape(str("" if value is None else value), quote=True)


def markdown_html(value) -> str:
    """Converts a Pages CMS value from Markdown to HTML.

    Fields declared as rich-text in .pages.yml go through here; every other
    field (titles, buttons, metadata) keeps using ``esc``.
    """
    if isinstance(value, (list, tuple)):
        # Lets a previous version of the content (separate paragraphs or
        # areas) keep building while it is migrated to the new format.
        source = "\n\n".join(str(part) for part in value if part is not None)
    else:
        source = "" if value is None else str(value)
    source = source.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not source:
        return ""
    return markdown.markdown(
        source,
        extensions=["extra"],
        output_format="html5",
    ).strip()


def media_url(path: str | None) -> str:
    """Normalizes a CMS image (/media/x, media/x, x) to a relative path."""
    if not path:
        return ""
    p = str(path).strip()
    if p.startswith(("http://", "https://", "//")):
        return p
    p = p.lstrip("/")
    if not p.startswith("media/"):
        p = "media/" + p
    if not (ROOT / p).exists():
        WARNINGS.append(f"Referenced image does not exist: {p}")
    return p


def site_url() -> str:
    """Public site URL, with trailing slash."""
    return str(CONTEXT["clinic_info"]["site"]["url"])


def absolute_url(path: str) -> str:
    """media/ path -> absolute site URL."""
    return site_url() + media_url(path)


def image_size(rel_path: str) -> tuple[int, int] | None:
    """(width, height) of a PNG or JPEG reading only its header."""
    try:
        data = (ROOT / rel_path).read_bytes()
    except OSError:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return int(w), int(h)
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return webp_size(data)
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xD8 or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if marker == 0xD9:
            break
        length = int.from_bytes(data[i + 2:i + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            height = int.from_bytes(data[i + 5:i + 7], "big")
            width = int.from_bytes(data[i + 7:i + 9], "big")
            return width, height
        i += 2 + length
    return None


def webp_size(data: bytes) -> tuple[int, int] | None:
    """(width, height) of a WebP (VP8, VP8L or VP8X) reading its header."""
    if data[12:16] == b"VP8X" and len(data) >= 30:
        return (int.from_bytes(data[24:27], "little") + 1,
                int.from_bytes(data[27:30], "little") + 1)
    if data[12:16] == b"VP8L" and len(data) >= 25:
        b = int.from_bytes(data[21:25], "little")
        return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    if data[12:16] == b"VP8 " and len(data) >= 30:
        return (int.from_bytes(data[26:28], "little") & 0x3FFF,
                int.from_bytes(data[28:30], "little") & 0x3FFF)
    return None


def img_tag(src: str, alt: str, attrs: str = "",
            size: tuple[int, int] | None = None) -> str:
    """<img> with width/height so the page does not jump while loading."""
    size = size or image_size(src)
    dim = f' width="{size[0]}" height="{size[1]}"' if size else ""
    return f'<img src="{esc(src)}"{dim} alt="{esc(alt)}"{attrs}>'


def image_html(path: str, alt: str, attrs: str = "") -> str:
    """<img> with the WebP version of the image and its dimensions.

    If prepare_media() converted this image (a PNG or JPEG uploaded to the
    CMS), the generated WebP is served; if it was already WebP, it is served
    as is. attrs starts with a space (e.g. ' loading="lazy" decoding="async"').
    """
    src = media_url(path)
    if not src:
        return ""
    converted = WEBP_SUBSTITUTES.get(src)
    if converted:
        webp, size = converted
        return img_tag(webp, alt, attrs, size)
    return img_tag(src, alt, attrs)


def icon_html(key: str | None) -> str:
    if key and key not in ICONS:
        sys.exit(f"Unknown icon in content/*.yml: {key!r} "
                 f"(valid values: {', '.join(ICONS)})")
    return ICONS.get(key or "", "")


def load_yaml(name: str) -> dict:
    path = CONTENT / f"{name}.yml"
    if not path.exists():
        sys.exit(f"Missing content file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        sys.exit(f"{path} must contain a mapping (key: value).")
    return data


def read_cname() -> str:
    path = SRC / "CNAME"
    if not path.exists():
        sys.exit(f"Missing site domain: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) != 1:
        sys.exit(f"{path} must contain a single valid domain.")
    domain = lines[0].strip()
    if len(domain) > 253 or not re.fullmatch(
            r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", domain):
        sys.exit(f"{path} must contain a single valid domain.")
    return domain


def raw_phone(phone: str) -> str:
    """Phone without spaces/parentheses/dashes for tel: and wa.me links."""
    return re.sub(r"[\s()\-]", "", phone)


# ---------------------------------------------------------------------------
# Resolution of the __file.path.field__ markers
# ---------------------------------------------------------------------------
# Format: first segment = file in content/ (without .yml), the rest is the
# path inside the YAML (numbers walk lists).
PLACEHOLDER_RE = re.compile(r"__(?P<ref>[a-z0-9_]+(?:\.[a-z0-9_]+)+)__")


class MissingFieldError(Exception):
    """Field referenced in a template that is found neither in the content
    (content/*.yml) nor in the type registry (.pages.yml).

    The build stops showing which field was looked up, in which template and
    why it was not found.
    """

    def __init__(self, template: str, route: str, reason: str):
        self.template = template
        self.route = route
        self.reason = reason
        super().__init__(
            f"Field not found: {route} (template {template}) — {reason}."
        )


# Derived fields: they exist neither in content/*.yml nor in .pages.yml; build.py
# computes them from other fields or from src/CNAME (e.g. the phone and the
# signature URL). These markers skip the .pages.yml registry.
DERIVED_FIELDS = frozenset({
    "clinic_info.site.url",
    "common.contact.phone_tel",
    "signature.web_label",
    "signature.web_url",
})


def resolve_data(template: str, ref: str, file: str, route: list[str],
                 context: dict) -> tuple:
    """Looks up the value of a marker in the loaded YAML.

    Returns (value, container): the field value and the node that holds it
    (for the special renderers that need sibling data, e.g. the alt text of a
    thumbnail).
    """
    data = context.get(file)
    if data is None:
        raise MissingFieldError(
            template, ref,
            f"content/{file}.yml does not exist (check the file name)")
    node = data
    parent = data
    for seg in route:
        parent = node
        if seg.isdigit():
            if not isinstance(node, (list, tuple)):
                raise MissingFieldError(
                    template, ref,
                    f"'{seg}' is not a list index in content/{file}.yml")
            idx = int(seg)
            if idx >= len(node):
                raise MissingFieldError(
                    template, ref,
                    f"index {idx} is out of range: content/{file}.yml has "
                    f"{len(node)} entries")
            node = node[idx]
        else:
            if not isinstance(node, dict) or seg not in node:
                raise MissingFieldError(
                    template, ref,
                    f"'{'.'.join(route)}' does not exist in content/{file}.yml")
            node = node[seg]
    return node, parent


# ---------------------------------------------------------------------------
# Template loops (@foreach) — lists that repeat on their own
# ---------------------------------------------------------------------------
# Cards and list items (services, modalities, process steps, blog posts and FAQ
# questions) are NOT written one by one in the index template: they are wrapped
# in an @foreach block that build.py repeats once per YAML element, so adding
# or removing entries in the CMS requires no HTML change.
#
# Template syntax:
#
#   <!-- @foreach:services.items -->
#   <div class="service-card" data-service="__services.items.n.id__"
#        onclick="openServiceModal('__services.items.n.id__')">
#       <h3>__services.items.n.title__</h3>
#       ...
#   </div>
#   <!-- @endforeach:services.items -->
#
# Inside the block, the "n" segment of a marker is replaced by the index of the
# current element (0, 1, 2...); the rest of the marker is resolved as usual.
# The __loop.index__ and __loop.index0__ markers give the position (1-based and
# 0-based) and are used for, e.g., the step number or the modal index
# (openModalityModal(index)). Markers of the section that do not depend on the
# element (e.g. __services.more_label__) are left untouched. If the list ends up
# empty, the block generates nothing. Loops cannot be nested.
LOOP_TOKENS = re.compile(
    r"<!--\s*@(?P<open>foreach:(?P<ref>[a-z0-9_]+(?:\.[a-z0-9_]+)+)|"
    r"endforeach(?::(?P<close_ref>[a-z0-9_]+(?:\.[a-z0-9_]+)+))?)\s*-->"
)


def expand_loop(template: str, ref: str, body: str, items: list) -> str:
    """Repeats the block body once per element of the list."""
    prefix = ref + ".n."
    fragments = []
    for idx in range(len(items)):

        def repl(m: "re.Match", i: int = idx) -> str:
            r = m.group("ref")
            if r.startswith(prefix):
                return f"__{ref}.{i}.{r[len(prefix):]}__"
            if r == "loop.index":
                return str(i + 1)
            if r == "loop.index0":
                return str(i)
            return m.group(0)

        fragments.append(PLACEHOLDER_RE.sub(repl, body).strip())
    # In the text files the elements of a loop are complete sections separated
    # by a blank line; single-line lists are kept together. In the HTML a
    # single line is always kept, as it has always been generated.
    if template.endswith(".txt") and any("\n" in f for f in fragments):
        return "\n\n".join(fragments)
    return "\n".join(fragments)


def expand_loops(template: str, source: str, context: dict) -> str:
    """Finds the @foreach blocks of the template and expands them."""
    parts = []
    stack: list[str] = []
    pos = 0
    for m in LOOP_TOKENS.finditer(source):
        token = m.group("open")
        if token.startswith("foreach:"):
            ref = m.group("ref")
            if stack:
                sys.exit(f"{template}: nested @foreach ('{ref}' inside "
                         f"'{stack[-1]}') not supported")
            parts.append(source[pos:m.start()])
            pos = m.end()
            stack.append(ref)
        else:
            if not stack:
                sys.exit(f"{template}: @endforeach without a previous @foreach")
            ref = stack.pop()
            close_ref = m.group("close_ref")
            if close_ref and close_ref != ref:
                sys.exit(f"{template}: @endforeach closes '{close_ref}' but "
                         f"the @foreach opened '{ref}'")
            body = source[pos:m.start()]
            file, _, route_str = ref.partition(".")
            node, _ = resolve_data(template, ref, file, route_str.split("."),
                                   context)
            if not isinstance(node, (list, tuple)):
                raise MissingFieldError(
                    template, ref,
                    f"'{ref}' is not a list in content/{file}.yml "
                    "(an @foreach only repeats over lists)")
            parts.append(expand_loop(template, ref, body, node))
            pos = m.end()
    if stack:
        sys.exit(f"{template}: @foreach '{stack[-1]}' without @endforeach")
    parts.append(source[pos:])
    return "".join(parts)


def resolve_type(template: str, ref: str, file: str, route: list[str],
                 fields_by_file: dict) -> dict:
    """Looks up the field in the type registry (.pages.yml).

    Returns the field definition (type, component, list...). If the field is
    not declared, the build fails: it is a configuration error.
    """
    fields = fields_by_file.get(file)
    if fields is None:
        raise MissingFieldError(
            template, ref,
            f"the collection '{file}' does not exist in .pages.yml (did you "
            "add it to the type registry?)")
    node = fields
    for i, seg in enumerate(route):
        if seg.isdigit():
            continue  # list index: the type is in the subfields
        field = next((f for f in node if f.get("name") == seg), None)
        if field is None:
            raise MissingFieldError(
                template, ref,
                f"the field '{seg}' is not declared in .pages.yml "
                f"(collection '{file}': {', '.join(f.get('name') or '?' for f in node)})")
        if i == len(route) - 1:
            return field
        sub = field.get("fields")
        if not sub:
            raise MissingFieldError(
                template, ref,
                f"the '{seg}' field of .pages.yml has no subfields to hold "
                f"the path '{ref}'")
        node = sub
    raise MissingFieldError(template, ref, "empty path in .pages.yml")


def render_field(value, field: dict) -> str:
    """Renders a value according to the type declared in .pages.yml."""
    if field.get("component") == "icon":
        return icon_html(value)
    if field.get("type") == "rich-text":
        return markdown_html(value)
    if field.get("type") == "image":
        return media_url(value)
    if isinstance(value, list):
        return "<br>".join(esc(v) for v in value)
    return esc(value)


# ---------------------------------------------------------------------------
# Special renderers (cases a .pages.yml type cannot express on its own).
# Template key -> exact path or "*" glob pattern -> function (value,
# container) -> HTML.
# ---------------------------------------------------------------------------
def render_modalities(value, parent: dict) -> str:
    """Hero: joins the modalities with "·" and keeps the last one unbroken."""
    parts = [p.strip() for p in str(value).split("·")]
    if len(parts) > 1:
        head = " · ".join(esc(p) for p in parts[:-1])
        return (f'{head} <span style="white-space: nowrap;">'
                f"· {esc(parts[-1])}</span>")
    return esc(parts[0])


def render_modality_content(value, parent: dict) -> str:
    """Modality: Markdown of the content + gallery of the consultation photos."""
    content = markdown_html(value)
    gallery = modality_gallery(parent.get("images") or [])
    return f"{content}\n{gallery}" if gallery else content


def render_blog_thumb(value, parent: dict) -> str:
    """Blog thumbnail: <picture> with the cover photo or a fallback icon."""
    image = image_html(value, parent.get("title", ""),
                       ' loading="lazy" decoding="async"')
    return image or icon_html("journal")


def render_keywords(value, parent: dict) -> str:
    """Keywords of the <head>: YAML list joined with commas."""
    if isinstance(value, str):
        return esc(value)
    return ", ".join(esc(keyword) for keyword in value or [])


def render_social_image(value, parent: dict) -> str:
    """Open Graph/Twitter image: absolute site URL."""
    return absolute_url(value)


def render_site_logo(value, parent: dict) -> str:
    return esc(site_url() + str(value).lstrip("/"))


# ---------------------------------------------------------------------------
# Text files (robots.txt, llms.txt, llms-full.txt) and sitemap.xml: markers
# are inserted as is, without HTML escaping or tags, and the Markdown of the
# sections is turned into plain text keeping its paragraphs.
# ---------------------------------------------------------------------------
def render_plain(value, parent: dict) -> str:
    """Value as is for a .txt file (no HTML escaping)."""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item).strip() for item in value if item is not None)
    return "" if value is None else str(value)


def render_comma_list(value, parent: dict) -> str:
    """List of strings or of objects with "title" -> text joined with commas."""
    if isinstance(value, (list, tuple)):
        parts = []
        for item in value:
            if isinstance(item, dict):
                item = item.get("title", "")
            if item is not None and str(item).strip():
                parts.append(str(item).strip())
        return ", ".join(parts)
    return render_plain(value, parent)


def markdown_text(value, parent: dict) -> str:
    """Markdown -> plain text keeping paragraphs and lists (.txt files).

    Removes emphasis and links but leaves the structure on separate lines so
    the text stays readable.
    """
    source = "" if value is None else str(value)
    source = source.replace("\r\n", "\n").replace("\r", "\n").strip()
    source = re.sub(r"\*\*(.+?)\*\*", r"\1", source, flags=re.S)
    source = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", source)
    return source


def render_sitemap_image(value, parent: dict) -> str:
    """<image:loc> of the sitemap: absolute URL of the published image.

    prepare_media() leaves the WebP version in WEBP_SUBSTITUTES, so that is
    what gets published; if the article has no cover, the site image is used.
    """
    path = media_url(value)
    substitute = WEBP_SUBSTITUTES.get(path)
    if substitute:
        path = substitute[0]
    return site_url() + (path or media_url(CONTEXT["clinic_info"]["social"]["image"]))


# ---------------------------------------------------------------------------
# Structured data (JSON-LD) — schema.org
# The whole block is generated here (it is not hand-written in the template)
# from content/clinic_info.yml and the rest of content/*.yml, so the data that
# search engines and AI assistants read never drifts from the real content of
# the site. The marker that triggers it is
# __clinic_info.structured_data__ (SPECIALS, below). The texts of each node
# (schema.org name, description, job title, topics covered, @id anchors...)
# live in clinic_info.yml -> schema; here only the schema.org vocabulary is
# left (the @type values and the @context).
# ---------------------------------------------------------------------------


def plain_text(md: str) -> str:
    """Markdown -> plain text (schema.org does not allow Markdown)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", str(md or ""))
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.M)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#`_>]", "", text)
    return " ".join(text.split())


def maps_coordinates(embed_url: str) -> tuple[float, float] | None:
    """Extracts (latitude, longitude) from the Google Maps iframe (!2dlon!3dlat)."""
    m = re.search(r"!2d(-?\d+\.\d+)!3d(-?\d+\.\d+)", str(embed_url or ""))
    return (float(m.group(2)), float(m.group(1))) if m else None


def build_jsonld() -> str:
    """Returns the JSON-LD (@graph) with the clinic, the professional, the
    service catalog, the FAQ and the articles."""
    try:
        return jsonld_graph()
    except KeyError as exc:
        sys.exit(f"content/clinic_info.yml: missing the field '{exc.args[0]}' "
                 "required by the JSON-LD block of src/index.html.")


def jsonld_graph() -> str:
    """Builds the JSON-LD graph with the data of content/*.yml."""
    c = CONTEXT
    info = c["clinic_info"]
    site = info["site"]
    schema = info["schema"]
    base = site_url()
    anchors = schema["anchors"]
    clinic_id = base + "#" + anchors["clinic"]
    person_id = base + "#" + anchors["person"]
    faq_id = base + "#" + anchors["faq"]
    blog_id = base + "#" + anchors["blog"]
    site_name = schema["site_name"]
    image = absolute_url(info["social"]["image"])
    logo = base + site["logo"]
    language = site["language"]
    contact = c["common"]["contact"]
    specialist = c["specialist"]
    instagram = (c["contact"].get("instagram") or {}).get("url", "")
    same_as = [u for u in (instagram, contact.get("maps_url", "")) if u]

    address_lines = list(contact.get("address_lines") or [])
    address = {
        "@type": "PostalAddress",
        "streetAddress": address_lines[0] if address_lines else "",
        "addressLocality": site["locality"],
        "addressRegion": site["region"],
        "addressCountry": site["country"],
    }
    if len(address_lines) > 1:
        m = re.match(r"(\d{5})", address_lines[1])
        if m:
            address["postalCode"] = m.group(1)

    # In-person municipalities + country for the online therapy.
    area_served = [{"@type": "City", "name": city}
                   for city in info.get("area_served") or []]
    online_area = info.get("online_area")
    if online_area:
        area_served.append({"@type": "Country", "name": online_area})

    person = {
        "@type": "Person",
        "@id": person_id,
        "name": specialist.get("name", ""),
        "jobTitle": schema["job_title"],
        "worksFor": {"@id": clinic_id},
        "knowsLanguage": [language],
        "sameAs": [u for u in (instagram,) if u],
    }
    credential = re.search(r"([A-Z]-\d+)", str(specialist.get("license", "")))
    if credential:
        person["hasCredential"] = {
            "@type": "EducationalOccupationalCredential",
            "credentialCategory": schema["credential_category"],
            "identifier": credential.group(1),
        }

    clinic = {
        "@type": ["MedicalBusiness", "Psychologist"],
        "@id": clinic_id,
        "name": site_name,
        "alternateName": f"{specialist.get('name', '')} {schema['role']}",
        "description": schema["description"],
        "url": base,
        "image": image,
        "logo": logo,
        "telephone": contact.get("phone", ""),
        "email": contact.get("mail", ""),
        "address": address,
        "priceRange": info.get("price_range", ""),
        "currenciesAccepted": site["currency"],
        "availableLanguage": [language],
        "areaServed": area_served,
        "knowsAbout": schema["knows_about"],
        "employee": {"@id": person_id},
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "name": schema["catalog_name"],
            "itemListElement": [
                {
                    "@type": "Offer",
                    "itemOffered": {
                        "@type": "Service",
                        "name": item.get("title", ""),
                        "description": plain_text(item.get("card_text", "")),
                        "serviceType": item.get("title", ""),
                        "provider": {"@id": clinic_id},
                    },
                }
                for item in c["services"]["items"]
            ],
        },
    }
    if same_as:
        clinic["sameAs"] = same_as
    coords = maps_coordinates(c["contact"].get("map_embed", ""))
    if coords:
        clinic["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": coords[0],
            "longitude": coords[1],
        }

    graph: list[dict] = [
        {
            "@type": "WebSite",
            "@id": base,
            "url": base,
            "name": site_name,
            "inLanguage": language,
            "publisher": {"@id": base},
        },
        clinic,
        person,
    ]

    faq_items = [
        {
            "@type": "Question",
            "name": item.get("question", ""),
            "acceptedAnswer": {"@type": "Answer",
                               "text": plain_text(item.get("answer", ""))},
        }
        for item in c["faq"].get("items") or []
    ]
    if faq_items:
        graph.append({
            "@type": "FAQPage",
            "@id": faq_id,
            "mainEntity": faq_items,
        })

    for index, post in enumerate(c["blog"].get("posts") or []):
        node = {
            "@type": "BlogPosting",
            "@id": f"{blog_id}-{index}",
            "headline": post.get("title", ""),
            "description": plain_text(post.get("excerpt", "")),
            "articleBody": plain_text(post.get("article", "")),
            "inLanguage": language,
            "author": {"@id": person_id},
            "publisher": {"@id": clinic_id},
            "mainEntityOfPage": {"@type": "WebPage", "url": blog_id},
        }
        cover = media_url(post.get("image", ""))
        node["image"] = base + cover if cover else image
        graph.append(node)

    return json.dumps(
        {"@context": "https://schema.org", "@graph": graph},
        ensure_ascii=False, indent=2)


SPECIALS: dict[str, dict] = {
    "src/index.html": {
        "hero.modalities": render_modalities,
        "blog.posts.*.image": render_blog_thumb,
        # The marker triggers the whole JSON-LD block of the page.
        "clinic_info.structured_data": lambda v, parent: build_jsonld(),
        # SEO: the keyword list is joined with commas and the social image is
        # published with its absolute URL.
        "clinic_info.seo.keywords": render_keywords,
        "clinic_info.social.image": render_social_image,
        # Images: <picture> with WebP + fallback, with width/height and the
        # right loading (the hero is immediate; the rest, on scroll).
        "hero.image": lambda v, parent: image_html(
            v, parent.get("image_alt", ""),
            ' fetchpriority="high" decoding="async"'),
        "specialist.image": lambda v, parent: image_html(
            v, parent.get("image_alt", ""), ' loading="lazy" decoding="async"'),
        # Full modality content: Markdown + consultation photos (optional:
        # only the modalities that declare them include them).
        "modalities.items.*.modal_content": render_modality_content,
    },
    "src/signature.html": {
        "clinic_info.site.logo": render_site_logo,
        # The signature shows the address on a single line.
        "common.contact.address_lines": lambda v, parent: " - ".join(
            esc(line) for line in v),
    },
    "src/sitemap.xml": {
        # The sitemap covers are published at the real path (WebP if they were
        # converted) and with the absolute site URL.
        "hero.image": render_sitemap_image,
        "specialist.image": render_sitemap_image,
        "blog.posts.*.image": render_sitemap_image,
    },
    "src/llms.txt": {
        # YAML lists (covered services, municipalities, topics...) in a single
        # line of plain text separated by commas.
        "clinic_info.area_served": render_comma_list,
        "clinic_info.schema.knows_about": render_comma_list,
        # The summarized process is the titles of its steps.
        "process.steps": render_comma_list,
        # Description of each service, without the card tags.
        "services.items.*.card_text": markdown_text,
        "*": render_plain,
    },
    "src/llms-full.txt": {
        "clinic_info.area_served": render_comma_list,
        "clinic_info.schema.knows_about": render_comma_list,
        "process.steps": render_comma_list,
        # Full Markdown of each section, as plain text.
        "services.items.*.card_text": markdown_text,
        "services.items.*.modal_content": markdown_text,
        "modalities.items.*.modal_content": markdown_text,
        "process.steps.*.text": markdown_text,
        "specialist.content": markdown_text,
        "faq.items.*.answer": markdown_text,
        "blog.posts.*.excerpt": markdown_text,
        "blog.posts.*.article": markdown_text,
        "*": render_plain,
    },
}


def apply_template(template_key: str, source: str, context: dict,
                   fields_by_file: dict) -> str:
    """Substitutes the __file.path.field__ markers of a template."""
    specials = SPECIALS.get(template_key, {})
    source = expand_loops(template_key, source, context)

    def repl(m: "re.Match") -> str:
        ref = m.group("ref")
        file, _, route_str = ref.partition(".")
        route = route_str.split(".")
        value, parent = resolve_data(template_key, ref, file, route, context)
        if ref in DERIVED_FIELDS:
            return esc(value)
        field = resolve_type(template_key, ref, file, route, fields_by_file)
        if ref in specials:
            return specials[ref](value, parent)
        for pattern, fn in specials.items():
            if "*" in pattern and fnmatch(ref, pattern):
                return fn(value, parent)
        return render_field(value, field)

    return PLACEHOLDER_RE.sub(repl, source)


def load_pages_types() -> dict[str, list]:
    """.pages.yml index -> {collection name: list of fields}."""
    path = ROOT / ".pages.yml"
    if not path.exists():
        sys.exit(f"Missing type registry: {path}")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    content = (cfg or {}).get("content")
    if not isinstance(content, list):
        sys.exit(f"{path}: the 'content' list was not found.")
    return {col["name"]: col.get("fields") or []
            for col in content if col.get("name")}


# ---------------------------------------------------------------------------
# Contact — content/common.yml -> the .neuro-* slots of the generated
# index.html. Single source of truth: the contact is written here, in the HTML;
# script.js does not touch it (its only job with data is filling the service
# and modality modals). The tel:/wa.me links of the signature use the derived
# key __common.contact.phone_tel__ (see DERIVED_FIELDS).
# ---------------------------------------------------------------------------
def fill_contact(doc: str, contact: dict) -> str:
    """Resolves every .neuro-* slot of the template in the HTML.

    Attributes: href of phone/WhatsApp/email/Maps.
    Text:       phone, email and address. The hero, the contact section and
                the footer all come from the same common.yml.
    """
    c = contact
    attrs = {
        "neuro-phone-link": ("href", f"tel:{raw_phone(c['phone'])}"),
        "neuro-whatsapp-link": ("href", f"https://wa.me/{raw_phone(c['phone']).lstrip('+')}"),
        "neuro-mail-link": ("href", f"mailto:{c['mail']}"),
        "neuro-address-link": ("href", c["maps_url"]),
    }
    texts = {
        "neuro-phone": esc(c["phone"]),
        "neuro-mail": esc(c["mail"]),
        "neuro-address": "<br>".join(esc(line) for line in c["address_lines"]),
    }

    def repl_tag(m: "re.Match") -> str:
        tag = m.group(0)
        cm = re.search(r'class="([^"]*)"', tag)
        if not cm:
            return tag
        classes = cm.group(1).split()
        for cls, (attr, value) in attrs.items():
            if cls in classes:
                if re.search(rf'\s{attr}="', tag):
                    tag = re.sub(rf'\s{attr}="[^"]*"', f' {attr}="{value}"',
                                 tag, count=1)
                else:
                    tag = tag[:-1].rstrip() + f' {attr}="{value}">'
        return tag

    def repl_elem(m: "re.Match") -> str:
        if m.group(1) != m.group(3):  # do not cross <a ...></span>
            return m.group(0)
        cm = re.search(r'class="([^"]*)"', m.group(2))
        if not cm:
            return m.group(0)
        classes = cm.group(1).split()
        for cls, text in texts.items():
            if cls in classes:
                return f"<{m.group(1)}{m.group(2)}>{text}</{m.group(3)}>"
        return m.group(0)

    doc = re.sub(r"<(?:a|img)\b[^>]*>", repl_tag, doc)
    return re.sub(r"<(a|span)\b([^>]*)></(a|span)>", repl_elem, doc)


# ---------------------------------------------------------------------------
# Modals: their full content is written into the HTML (hidden .card-full
# blocks of each card) so that search engines and AI assistants read it
# without JavaScript; script.js only copies it into the modal. Services are
# opened by their "id" field (openServiceModal('neuro') looks up
# data-service="neuro"), so it must exist and be unique.
# ---------------------------------------------------------------------------
def validate_service_ids(c: dict) -> None:
    seen: set[str] = set()
    for item in c["services"]["items"]:
        sid = item.get("id")
        if not sid:
            sys.exit("A service in content/services.yml has no 'id'. "
                     "It is mandatory: it opens its modal "
                     "(openServiceModal('id')).")
        if sid in seen:
            sys.exit(f"Duplicated identifier in content/services.yml: "
                     f"'{sid}'. It must be unique per service.")
        seen.add(sid)


def modality_gallery(images: list[dict]) -> str:
    """Generates the optional grid of photos inside a modal."""
    figures = []
    for image in images:
        src = media_url(image.get("image"))
        if src:
            photo = image_html(
                image.get("image"), image.get("alt", ""),
                ' loading="lazy" decoding="async" onerror="this.remove()"')
            figures.append(
                '<figure class="modality-gallery-item">'
                '<i class="bi bi-camera"></i>'
                f'{photo}</figure>'
            )
        else:
            figures.append(
                '<figure class="modality-gallery-item">'
                '<i class="bi bi-camera"></i></figure>'
            )
    if not figures:
        return ""
    return ('<div class="modality-gallery">\n'
            + "\n".join(f"    {f}" for f in figures)
            + "\n</div>")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build_context() -> dict:
    """Loads content/*.yml and adds the derived fields (DERIVED_FIELDS)."""
    domain = read_cname()
    context = {p.stem: load_yaml(p.stem) for p in sorted(CONTENT.glob("*.yml"))}
    base_url = f"https://{domain}/"
    context["clinic_info"]["site"]["url"] = base_url
    context["signature"]["web_label"] = domain
    context["signature"]["web_url"] = base_url.rstrip("/")
    contact = context["common"]["contact"]
    contact["phone_tel"] = f"tel:{raw_phone(contact['phone'])}"
    return context


# ---------------------------------------------------------------------------
# Images — media/ -> _site/media/
# Photos uploaded from Pages CMS can arrive as PNG or JPEG. When building
# (locally and on every publish) they are converted to WebP and only that
# version is published, which weighs much less; the original is not published.
# This way the site always serves light images without anyone converting files
# by hand. Requires Pillow (pip install pillow).
# ---------------------------------------------------------------------------
def pillow_image():
    """Imports PIL.Image; if missing, stops the build with a clear message."""
    try:
        from PIL import Image
    except ModuleNotFoundError:
        sys.exit("Missing Pillow to convert the images to WebP.\n"
                 "Install it with: pip install pillow\n"
                 "(or run the build with: "
                 "uv run --with pyyaml --with markdown --with pillow "
                 "python scripts/build.py)")
    return Image


def convert_to_webp(src: Path, dst: Path) -> tuple[int, int]:
    """Converts a PNG/JPEG from media/ to WebP and writes it to dst."""
    image = pillow_image()
    with image.open(src) as original:
        if original.mode not in ("RGB", "RGBA"):
            mode = "RGBA" if "transparency" in original.info else "RGB"
            converted = original.convert(mode)
        else:
            converted = original
        size = converted.size
        converted.save(dst, "WEBP", quality=82, method=6)
    return size


def prepare_media() -> None:
    """Copies media/ to _site/media/ converting the PNG/JPEG to WebP."""
    source_dir = ROOT / "media"
    if not source_dir.is_dir():
        return
    dest_dir = OUT / "media"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(source_dir.iterdir()):
        if not src.is_file() or src.name in MEDIA_EXCLUDES:
            continue
        if src.suffix.lower() in RASTER_FORMATS and src.name not in KEEP_AS_IS:
            webp = dest_dir / (src.stem + ".webp")
            size = convert_to_webp(src, webp)
            WEBP_SUBSTITUTES[f"media/{src.name}"] = (f"media/{webp.name}", size)
            print(f"  {src.name} -> {webp.name} ({size[0]}x{size[1]})")
        else:
            shutil.copy2(src, dest_dir / src.name)


def main() -> None:
    global CONTEXT
    context = build_context()
    validate_service_ids(context)
    CONTEXT = context
    fields_by_file = load_pages_types()

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    # Before rendering: converts the images to WebP so the templates can
    # already link to the final version.
    prepare_media()

    for key, path in TEMPLATES.items():
        source = path.read_text(encoding="utf-8")
        doc = apply_template(key, source, context, fields_by_file)
        if key == "src/index.html":
            doc = fill_contact(doc, context["common"]["contact"])
        (OUT / path.name).write_text(doc, encoding="utf-8")

    for src, name in STATIC_FILES:
        if not src.exists():
            sys.exit(f"Missing static file: {src}")
        shutil.copy2(src, OUT / name)

    print(f"OK: site generated in {OUT}")
    for warning in WARNINGS:
        print(f"WARNING: {warning}")


if __name__ == "__main__":
    try:
        main()
    except MissingFieldError as exc:
        sys.exit(str(exc))
