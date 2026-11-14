#!/usr/bin/env python3
"""Generates a preview page of every icon in build.py's ICONS dict.

Writes tmp/icons-preview.html (gitignored) with a card per icon, so the
whole selector can be checked at a glance before publishing. The icons are
imported from build.py (the single source of truth), so the page never
drifts from what the site renders.

Usage
-----
    uv run --with pyyaml --with markdown python scripts/icons_preview.py
    # then open tmp/icons-preview.html
"""

from __future__ import annotations

from pathlib import Path

import build

OUT = Path(__file__).resolve().parent.parent / "tmp" / "icons-preview.html"

# Same Bootstrap Icons CDN as src/index.html, so the "bi bi-*" icons of the
# dict look exactly like the ones on the site.
BOOTSTRAP_CSS = (
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css"
)


def main() -> None:
    cards = "\n".join(
        f'        <div class="card"><span class="icon">{icon_html}</span>'
        f"<code>{name}</code></div>"
        for name, icon_html in sorted(build.ICONS.items())
    )
    page = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Iconos disponibles</title>
<link rel="stylesheet" href="{BOOTSTRAP_CSS}">
<style>
body {{ margin: 2rem; font-family: system-ui, sans-serif; color: #222; background: #fff; }}
.dark {{ color: #eee; background: #1a1a1a; }}
.dark .card {{ border-color: #444; }}
h1 {{ font-size: 1.4rem; }}
button {{ margin-bottom: 1rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 1rem; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; align-items: center; gap: .75rem; }}
.icon {{ font-size: 48px; line-height: 1; }}
code {{ font-size: .78rem; }}
</style>
</head>
<body>
<h1>Iconos disponibles ({len(build.ICONS)})</h1>
<button onclick="document.body.classList.toggle('dark')">Cambiar fondo</button>
<div class="grid">
{cards}
</div>
</body>
</html>
"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"OK: {OUT}")


if __name__ == "__main__":
    main()
