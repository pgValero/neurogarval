#!/usr/bin/env python3
"""build.py — build mínimo del sitio estático neurogarval.es.

Qué hace
--------
1. Lee el contenido editable de Pages CMS:  content/*.yml
2. Convierte a HTML los campos de texto largo escritos en Markdown.
3. Regenera las regiones delimitadas por
      <!-- pages:begin NOMBRE -->  ...  <!-- pages:end NOMBRE -->
   en index.html (22) y firma.html (4); el resto de la plantilla
   HTML/CSS se queda intacto.
4. Escribe el contacto de content/settings.yml directamente en
   index.html: los huecos .neuro-* (teléfono, WhatsApp, email,
   dirección, Maps y logo) quedan resueltos en el HTML, sin JavaScript.
5. Genera _site/data.js (window.SITE_DATA: servicios, modalidades e iconos),
   que script.js usa al abrir sus respectivos modales.
6. Copia los estáticos (CSS, JS, CNAME, favicons, PDFs) y media/ a _site/.

Uso
---
    pip install pyyaml markdown  # dependencias del generador
    python build.py              # genera ./_site

La GitHub Action (.github/workflows/deploy.yml) hace exactamente esto en
cada push a main y publica _site/ en GitHub Pages. No hay framework ni
generador de sitio: solo este script.

Contrato de regiones (nombre -> fichero de datos) en INDEX_REGIONS y
FIRMA_REGIONS más abajo; si añades una región al HTML, regístrala ahí.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

try:
    import markdown
    import yaml
except ImportError as exc:  # pragma: no cover
    missing = "Markdown" if exc.name == "markdown" else "PyYAML"
    sys.exit(f"Falta {missing}. Instálalo con:  pip install pyyaml markdown")

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
OUT = ROOT / "_site"

# ---------------------------------------------------------------------------
# ICONOS — única fuente de verdad (claves = values del campo "icono" en
# .pages.yml). Cada valor es el HTML que se inserta en la tarjeta/modal.
# ---------------------------------------------------------------------------
SVG_ATTRS = (
    'xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"'
)


def svg(paths: str) -> str:
    return f"<svg {SVG_ATTRS}>{paths}</svg>"


ICONS: dict[str, str] = {
    # Iconos "inline SVG" (heredan tamaño/color del contenedor)
    "brain": svg(
        '<path d="M12 18V5"/><path d="M15 13a4.17 4.17 0 0 1-3-4 4.17 4.17 0 0 1 3 4"/>'
        '<path d="M17.598 6.5A3 3 0 1 0 12 5a3 3 0 1 0-5.598 1.5"/>'
        '<path d="M17.997 5.125a4 4 0 0 1 2.526 5.77"/><path d="M18 18a4 4 0 0 0 2-7.464"/>'
        '<path d="M19.967 17.483A4 4 0 1 1 12 18a4 4 0 1 1-7.967-.517"/>'
        '<path d="M6 18a4 4 0 0 1 2-7.464"/><path d="M6.003 5.125a4 4 0 0 0 2.526 5.77"/>'
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
    # Iconos de fuente Bootstrap Icons (incluida en index.html)
    "building": '<i class="bi bi-building"></i>',
    "laptop": '<i class="bi bi-laptop"></i>',
    "house": '<i class="bi bi-house-door"></i>',
    "journal": '<i class="bi bi-journal-text"></i>',
}

# Archivos estáticos que se copian tal cual a _site/.
STATIC_FILES = ["styles.css", "script.js", "CNAME", "favicon.svg",
                "aviso_legal.pdf", "tarjeta.pdf"]

# Avisos no fatales (p. ej. fotos de modalidades aún no subidas).
WARNINGS: list[str] = []


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def esc(value) -> str:
    """Escapa texto plano para insertarlo en HTML (no usar con Markdown)."""
    return html.escape(str("" if value is None else value), quote=True)


def markdown_html(value) -> str:
    """Convierte un valor de Pages CMS en Markdown a HTML.

    Los campos de contenido largo se guardan como Markdown. Esta función es
    el único punto por el que ese texto entra en el HTML: los títulos,
    botones y metadatos siguen usando ``esc`` porque son texto plano.
    """
    if isinstance(value, (list, tuple)):
        # Permite que una versión anterior del contenido (párrafos o áreas
        # separados) siga construyendo durante la migración al nuevo formato.
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


def ind(text: str, spaces: int) -> str:
    """Sangría adicional para bloques anidados dentro de una región."""
    pad = " " * spaces
    return "\n".join(pad + line if line else line for line in text.split("\n"))


def media_url(path: str | None) -> str:
    """Normaliza una imagen del CMS (/media/x, media/x, x) a ruta relativa."""
    if not path:
        return ""
    p = str(path).strip()
    if p.startswith(("http://", "https://", "//")):
        return p
    p = p.lstrip("/")
    if not p.startswith("media/"):
        p = "media/" + p
    if not (ROOT / p).exists():
        WARNINGS.append(f"La imagen referenciada no existe: {p}")
    return p


def abs_url(base: str, path: str) -> str:
    """URL absoluta (para meta tags): base + ruta normalizada."""
    if not path:
        return ""
    if path.startswith(("http://", "https://")):
        return path
    return base.rstrip("/") + "/" + path.lstrip("/")


def icon_html(key: str | None) -> str:
    if key and key not in ICONS:
        sys.exit(f"Icono desconocido en content/*.yml: {key!r} "
                 f"(valores válidos: {', '.join(ICONS)})")
    return ICONS.get(key or "", "")


def load_yaml(name: str) -> dict:
    path = CONTENT / f"{name}.yml"
    if not path.exists():
        sys.exit(f"Falta el fichero de contenido: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        sys.exit(f"{path} debe contener un mapa (clave: valor).")
    return data


def section_header(heading: str, lead: str) -> str:
    return (
        f"<h2>{esc(heading)}</h2>\n"
        '<div class="divider"></div>\n'
        '<div class="markdown-content">\n'
        f"{ind(markdown_html(lead), 4)}\n"
        "</div>"
    )


def menu_items(settings: dict, desktop: bool) -> str:
    parts = []
    for item in settings.get("menu", []):
        if bool(item.get("desktop")) != desktop:
            continue
        label, href = esc(item["label"]), esc(item["href"])
        if desktop:
            parts.append(f'<li><a href="{href}">{label}</a></li>')
        else:
            parts.append(f'<a href="{href}" onclick="toggleMenu()">{label}</a>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Regiones de index.html
# ---------------------------------------------------------------------------
def r_head_seo(c: dict) -> str:
    s, seo, jl = c["settings"], c["settings"]["seo"], c["settings"]["jsonld"]
    base = s["site"]["base_url"].rstrip("/")
    canonical = base + "/"
    og_image = abs_url(base, media_url(seo.get("og_image")))
    addr = jl["address"]
    jsonld = {
        "@context": "https://schema.org",
        "@type": "MedicalBusiness",
        "name": jl.get("name"),
        "alternateName": jl.get("alternate_name") or None,
        "image": og_image,
        "url": canonical,
        "telephone": re.sub(r"[\s()\-]", "", s["contact"]["phone"]),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": addr.get("street"),
            "addressLocality": addr.get("locality"),
            "addressRegion": addr.get("region"),
            "postalCode": addr.get("postal_code"),
            "addressCountry": addr.get("country"),
        },
        "priceRange": jl.get("price_range"),
        "founder": {"@type": "Person", "name": jl.get("founder")},
    }
    jsonld = {k: v for k, v in jsonld.items() if v is not None}
    lines = [
        "<!-- SEO Básico -->",
        f"<title>{esc(seo['title'])}</title>",
        f'<meta name="description" content="{esc(seo["description"])}">',
        f'<meta name="keywords" content="{esc(seo["keywords"])}">',
        f'<link rel="canonical" href="{esc(canonical)}">',
        "",
        "<!-- Open Graph / Redes Sociales -->",
        '<meta property="og:type" content="website">',
        '<meta property="og:locale" content="es">',
        f'<meta property="og:title" content="{esc(seo["og_title"])}">',
        f'<meta property="og:description" content="{esc(seo["og_description"])}">',
        f'<meta property="og:image" content="{esc(og_image)}">',
        f'<meta property="og:url" content="{esc(canonical)}">',
        "",
        "<!-- Datos Estructurados (Schema.org) -->",
        '<script type="application/ld+json">',
        json.dumps(jsonld, ensure_ascii=False, indent=2),
        "</script>",
    ]
    return "\n".join(lines)


def r_hero(c: dict) -> str:
    h = c["home"]["hero"]
    accent = str(h.get("title_accent") or "").strip()
    title = esc(h["title"]) + (f" <i>{esc(accent)}</i>" if accent else "")
    parts = [p.strip() for p in str(h["modalities"]).split("·")]
    if len(parts) > 1:
        head = " · ".join(esc(p) for p in parts[:-1])
        modalities = (f'{head} <span style="white-space: nowrap;">'
                      f"· {esc(parts[-1])}</span>")
    else:
        modalities = esc(parts[0])
    return "\n".join([
        f'<span class="badge">{esc(h["badge"])}</span>',
        f"<h1>{title}</h1>",
        f'<span class="modalities-text">{modalities}</span>',
        '<div class="markdown-content">',
        ind(markdown_html(h["paragraph"]), 4),
        "</div>",
        "",
        '<div id="hero-promo">'
        f'<i class="bi bi-info-circle-fill"></i><span>{esc(h["promo"])}</span>'
        "</div>",
    ])


def r_hero_img(c: dict) -> str:
    h = c["home"]["hero"]
    return f'<img src="{media_url(h.get("image"))}" alt="{esc(h.get("image_alt"))}">'


def r_services_grid(c: dict) -> str:
    sv = c["home"]["services"]
    chunks = []
    for i, item in enumerate(sv["items"]):
        onkeydown = (
            f"if(event.key==='Enter'||event.key===' '){{event.preventDefault();"
            f"openServiceModal({i})}}"
        )
        chunks.append("\n".join([
            f'<div class="service-card" role="button" tabindex="0" '
            f'aria-haspopup="dialog" data-service="{i}" '
            f'onclick="openServiceModal({i})" onkeydown="{onkeydown}">',
            f'    <div class="service-icon">{icon_html(item.get("icon"))}</div>',
            f'    <h3>{esc(item["title"])}</h3>',
            '    <div class="markdown-content">',
            ind(markdown_html(item["card_text"]), 8),
            "    </div>",
            f'    <span class="service-more">{esc(sv["more_label"])} '
            '<i class="bi bi-arrow-right"></i></span>',
            "</div>",
        ]))
    return "\n".join(chunks)


def r_services_areas(c: dict) -> str:
    sv = c["home"]["services"]
    # La introducción y las áreas viven en un único campo Markdown. El
    # contenedor conserva el estilo de lista con check del bloque original.
    areas = sv.get("areas", "")
    if isinstance(areas, (list, tuple)):
        # Compatibilidad con el esquema anterior, que separaba cada área.
        intro = sv.get("areas_intro", "")
        items = "\n".join(f"- {area}" for area in areas)
        areas = f"{intro}\n\n{items}".strip()
    elif not areas and sv.get("areas_intro"):
        areas = sv["areas_intro"]
    content = markdown_html(areas)
    if not content:
        return ""
    return (
        '<div class="check-list markdown-content">\n'
        + ind(content, 4)
        + "\n</div>"
    )


def r_modalities_grid(c: dict) -> str:
    modalities = c["home"]["modalities"]
    chunks = []
    for i, item in enumerate(modalities["items"]):
        onkeydown = (
            f"if(event.key==='Enter'||event.key===' '){{event.preventDefault();"
            f"openModalityModal({i})}}"
        )
        chunks.append("\n".join([
            f'<div class="modality-item" role="button" tabindex="0" '
            f'aria-haspopup="dialog" data-modality="{i}" '
            f'onclick="openModalityModal({i})" onkeydown="{onkeydown}">',
            f'    <div class="modality-icon">{icon_html(item.get("icon"))}</div>',
            '    <div class="modality-content">',
            f'        <h4>{esc(item["title"])}</h4>',
            '        <div class="markdown-content">',
            ind(markdown_html(item["text"]), 12),
            "        </div>",
            f'        <span class="service-more">{esc(modalities["more_label"])} '
            '<i class="bi bi-arrow-right"></i></span>',
            "    </div>",
            "</div>",
        ]))
    return "\n\n".join(chunks)


def modality_gallery(images: list[dict]) -> str:
    """Genera la cuadrícula opcional de fotos dentro de un modal."""
    figures = []
    for image in images:
        src = media_url(image.get("image"))
        alt = esc(image.get("alt"))
        if src:
            figures.append(
                f'<figure class="modality-gallery-item">'
                '<i class="bi bi-camera"></i>'
                f'<img src="{esc(src)}" alt="{alt}" loading="lazy" '
                'onerror="this.remove()"></figure>'
            )
        else:
            figures.append(
                '<figure class="modality-gallery-item">'
                '<i class="bi bi-camera"></i></figure>'
            )
    if not figures:
        return ""
    return ('<div class="modality-gallery">\n'
            + ind("\n".join(figures), 4)
            + "\n</div>")


def modality_modal_html(item: dict) -> str:
    """Convierte a HTML el Markdown y añade las fotos de la modalidad."""
    content = markdown_html(item.get("modal_content", ""))
    gallery = modality_gallery(item.get("images") or [])
    return f"{content}\n{gallery}" if gallery else content


def r_process_grid(c: dict) -> str:
    chunks = []
    for n, step in enumerate(c["home"]["process"]["steps"], start=1):
        chunks.append("\n".join([
            '<div class="process-step">',
            '    <div class="process-num">',
            f'        <span class="process-icon">{icon_html(step.get("icon"))}</span>',
            f'        <span class="process-index">{n}</span>',
            "    </div>",
            f'    <h4>{esc(step["title"])}</h4>',
            '    <div class="markdown-content">',
            ind(markdown_html(step["text"]), 8),
            "    </div>",
            "</div>",
        ]))
    return "\n\n".join(chunks)


def r_about(c: dict) -> str:
    a = c["home"]["about"]
    # Todo el texto de la especialista se edita en un único campo Markdown.
    content = markdown_html(a.get("content", a.get("paragraphs", "")))
    return "\n".join([
        '<div class="about-image">',
        f'    <img src="{media_url(a.get("image"))}" alt="{esc(a.get("image_alt"))}">',
        '    <div class="col-card">',
        f'        <span class="name">{esc(a["name"])}</span>',
        f'        <span class="label">{esc(a["license"])}</span>',
        "    </div>",
        "</div>",
        '<div class="about-content">',
        f'    <h2>{esc(a["heading"])}</h2>',
        '    <div class="divider"></div>',
        '    <div class="markdown-content">',
        ind(content, 8),
        "    </div>",
        "</div>",
    ])


def r_blog_grid(c: dict) -> str:
    b = c["home"]["blog"]
    cards = []
    for post in b["posts"]:
        img = media_url(post.get("image"))
        if img:
            thumb = (f'<img src="{img}" alt="{esc(post["title"])}" '
                     'loading="lazy">')
        else:
            thumb = icon_html("journal")
        # El texto visible de cada artículo se escribe como un único campo
        # Markdown y se convierte aquí antes de insertarlo en la tarjeta.
        article = markdown_html(post.get("excerpt", post.get("content", "")))
        cards.append("\n".join([
            '<article class="blog-card">',
            f'    <div class="blog-thumb">{thumb}</div>',
            '    <div class="blog-content">',
            f'        <span class="blog-date">{esc(post["date"])}</span>',
            f'        <h4>{esc(post["title"])}</h4>',
            '        <div class="markdown-content">',
            ind(article, 12),
            "        </div>",
            f'        <a href="{esc(post.get("url") or "#")}" class="read-more">'
            f'{esc(b["read_more"])} <i class="bi bi-arrow-right"></i></a>',
            "    </div>",
            "</article>",
        ]))
    return "\n".join(cards)


def r_faq_list(c: dict) -> str:
    items = []
    for item in c["home"]["faq"]["items"]:
        items.append("\n".join([
            '<details class="faq-item">',
            f'    <summary>{esc(item["question"])}</summary>',
            '    <div class="markdown-content">',
            ind(markdown_html(item["answer"]), 8),
            "    </div>",
            "</details>",
        ]))
    return "\n\n".join(items)


def r_contact_header(c: dict) -> str:
    k = c["home"]["contact"]
    return "\n".join([
        f'<h2>{esc(k["heading"])}</h2>',
        '<div class="divider"></div>',
        f'<strong>{esc(k["highlight"])}</strong>',
        '<div class="markdown-content">',
        ind(markdown_html(k["lead"]), 4),
        "</div>",
    ])


def r_contact_instagram(c: dict) -> str:
    ig = c["settings"]["contact"]["instagram"]
    return "\n".join([
        f'<a href="{esc(ig["url"])}" target="_blank" class="contact-item">',
        '    <div class="contact-icon"><i class="bi bi-instagram"></i></div>',
        '    <h4>Instagram</h4>',
        f'    <span>{esc(ig["handle"])}</span>',
        "</a>",
    ])


def r_contact_map(c: dict) -> str:
    src = esc(c["home"]["contact"]["map_embed"])
    return "\n".join([
        "<iframe",
        f'    src="{src}"',
        '    width="600"',
        '    height="450"',
        '    style="border:0;"',
        '    allowfullscreen=""',
        '    loading="lazy"',
        '    referrerpolicy="no-referrer-when-downgrade">',
        "</iframe>",
    ])


def r_footer_info(c: dict) -> str:
    s = c["settings"]
    f = s["footer"]
    lines = "<br>".join(esc(line) for line in f["lines"])
    return "\n".join([
        f'<img src="{media_url(s["site"]["logo"])}" alt="NeuroGarval" '
        'class="footer-logo neuro-logo">',
        f"<p>{lines}</p>",
        "<br>",
        f'<a href="{esc(f["legal_file"])}">{esc(f["legal_label"])}</a>',
    ])


def r_footer_copyright(c: dict) -> str:
    return f'&copy; {esc(c["settings"]["footer"]["copyright"])}'


INDEX_REGIONS: dict[str, "callable"] = {
    "head-seo": r_head_seo,
    "mobile-menu": lambda c: menu_items(c["settings"], desktop=False),
    "nav-desktop": lambda c: menu_items(c["settings"], desktop=True),
    "hero": r_hero,
    "hero-img": r_hero_img,
    "services-header": lambda c: section_header(
        c["home"]["services"]["heading"], c["home"]["services"]["lead"]),
    "services-grid": r_services_grid,
    "services-areas": r_services_areas,
    "modalities-header": lambda c: section_header(
        c["home"]["modalities"]["heading"], c["home"]["modalities"]["lead"]),
    "modalities-grid": r_modalities_grid,
    "process-header": lambda c: section_header(
        c["home"]["process"]["heading"], c["home"]["process"]["lead"]),
    "process-grid": r_process_grid,
    "about": r_about,
    "blog-header": lambda c: section_header(
        c["home"]["blog"]["heading"], c["home"]["blog"]["lead"]),
    "blog-grid": r_blog_grid,
    "faq-header": lambda c: section_header(
        c["home"]["faq"]["heading"], c["home"]["faq"]["lead"]),
    "faq-list": r_faq_list,
    "contact-header": r_contact_header,
    "contact-instagram": r_contact_instagram,
    "contact-map": r_contact_map,
    "footer-info": r_footer_info,
    "footer-copyright": r_footer_copyright,
}

# ---------------------------------------------------------------------------
# Inyección de regiones
# ---------------------------------------------------------------------------
REGION_RE = re.compile(
    r"(?P<indent>[ \t]*)<!--\s*pages:begin\s+(?P<name>[a-z0-9\-]+)\s*-->"
    r"(?P<body>.*?)"
    r"<!--\s*pages:end\s+(?P=name)\s*-->",
    re.DOTALL,
)


def apply_regions(source: str, renderers: dict, fname: str) -> str:
    found: set[str] = set()

    def repl(match: "re.Match") -> str:
        name = match.group("name")
        if name not in renderers:
            sys.exit(f"{fname}: la región '{name}' no tiene renderer en build.py.")
        found.add(name)
        indent = match.group("indent")
        body = renderers[name](CONTEXT)
        inner = "\n".join(
            (indent + line) if line.strip() else ""
            for line in body.split("\n")
        )
        return (f"{indent}<!-- pages:begin {name} -->\n"
                f"{inner}\n"
                f"{indent}<!-- pages:end {name} -->")

    result = REGION_RE.sub(repl, source)
    missing = set(renderers) - found
    if missing:
        sys.exit(f"{fname}: faltan regiones en la plantilla: {sorted(missing)}")
    return result


# ---------------------------------------------------------------------------
# Contacto — content/settings.yml -> huecos .neuro-* de index.html.
# Fuente única: el contacto se escribe aquí, en el HTML; script.js no lo
# toca (su único trabajo con datos es rellenar los modales de servicios y
# modalidades).
# ---------------------------------------------------------------------------
def fill_contact(doc: str, settings: dict) -> str:
    """Resuelve en el HTML todos los huecos .neuro-* de la plantilla.

    Atributos: href de teléfono/WhatsApp/email/Maps y src del logo.
    Texto:     teléfono, email y dirección. Cabecera, hero, sección de
               contacto y footer salen todos del mismo settings.yml.
    """
    c = settings["contact"]
    raw_phone = re.sub(r"[\s()\-]", "", c["phone"])
    attrs = {
        "neuro-phone-link": ("href", f"tel:{raw_phone}"),
        "neuro-whatsapp-link": ("href", f"https://wa.me/{raw_phone.lstrip('+')}"),
        "neuro-mail-link": ("href", f"mailto:{c['mail']}"),
        "neuro-address-link": ("href", c["maps_url"]),
        "neuro-logo": ("src", media_url(settings["site"]["logo"])),
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
        if m.group(1) != m.group(3):  # no cruzar <a ...></span>
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
# Regiones de firma.html (contacto desde settings.yml; texto propio de la
# firma desde content/firma.yml)
# ---------------------------------------------------------------------------
def r_firma_logo(c: dict) -> str:
    web = c["firma"]["web_url"].rstrip("/")
    logo = media_url(c["settings"]["site"]["logo"])
    return "\n".join([
        '<td style="padding: 10px; vertical-align: middle; text-align: center; '
        'background-color: #78A2D2; width: fit-content;">',
        f'  <img src="{web}/{logo}" alt="NeuroGarval" width="150px" '
        'style="display: block;">',
    ])


def r_firma_identity(c: dict) -> str:
    f = c["firma"]
    return "\n".join([
        f'<div style="font-size: 18px; font-weight: bold; color: #29335C;">'
        f'{esc(f["name"])}</div>',
        f'<div style="font-size: 16px; color: #333333;">{esc(f["license"])}</div>',
        f'<div style="font-size: 14px; color: #29335C; font-weight: 600; '
        f'margin-bottom: 5px;">{esc(f["role"])}</div>',
    ])


def r_firma_contact(c: dict) -> str:
    f = c["firma"]
    contact = c["settings"]["contact"]
    raw_phone = re.sub(r"[\s()\-]", "", contact["phone"])
    address = " - ".join(contact["address_lines"])
    a = 'style="color: #666666; text-decoration: none;"'
    return "\n".join([
        '<div style="font-size: 13px; color: #666666;">',
        f'  <a href="tel:{raw_phone}" {a}>{esc(contact["phone"])}</a> |',
        f'  <a href="{esc(f["web_url"])}" {a}>{esc(f["web_label"])}</a><br>',
        f'  <a href="{esc(contact["maps_url"])}" {a}>{esc(address)}</a>',
        "</div>",
    ])


def r_firma_legal(c: dict) -> str:
    f = c["firma"]
    return "\n".join([
        '<td colspan="2" style="padding-top: 20px; font-size: 10px; '
        'color: #999999; line-height: 1.2; text-align: justify;">',
        f'  {esc(f["legal_aviso"])}<br><br>',
        f'  {esc(f["legal_proteccion"])}',
    ])


FIRMA_REGIONS: dict[str, "callable"] = {
    "firma-logo": r_firma_logo,
    "firma-identity": r_firma_identity,
    "firma-contact": r_firma_contact,
    "firma-legal": r_firma_legal,
}

# ---------------------------------------------------------------------------
# data.js — puente con script.js (solo modales: servicios, modalidades e iconos).
# El contacto NO viaja aquí: se escribe en index.html con fill_contact().
# ---------------------------------------------------------------------------
def write_data_js(c: dict) -> None:
    services = [
        {
            "title": item["title"],
            "icon": item.get("icon", ""),
            "html": markdown_html(item["modal_content"]),
        }
        for item in c["home"]["services"]["items"]
    ]
    modalities = [
        {
            "title": item["title"],
            "icon": item.get("icon", ""),
            "html": modality_modal_html(item),
        }
        for item in c["home"]["modalities"]["items"]
    ]
    payload = {"services": services, "modalities": modalities, "icons": ICONS}
    js = ("// Generado por build.py desde content/*.yml — NO editar a mano.\n"
          "window.SITE_DATA = "
          + json.dumps(payload, ensure_ascii=False, indent=2)
          + ";\n")
    (OUT / "data.js").write_text(js, encoding="utf-8")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
CONTEXT: dict = {}


def main() -> None:
    global CONTEXT
    CONTEXT = {
        "settings": load_yaml("settings"),
        "home": load_yaml("home"),
        "firma": load_yaml("firma"),
    }

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    index_src = (ROOT / "index.html").read_text(encoding="utf-8")
    index_doc = apply_regions(index_src, INDEX_REGIONS, "index.html")
    index_doc = fill_contact(index_doc, CONTEXT["settings"])
    (OUT / "index.html").write_text(index_doc, encoding="utf-8")

    firma_src = (ROOT / "firma.html").read_text(encoding="utf-8")
    (OUT / "firma.html").write_text(
        apply_regions(firma_src, FIRMA_REGIONS, "firma.html"), encoding="utf-8")

    write_data_js(CONTEXT)

    for name in STATIC_FILES:
        src = ROOT / name
        if not src.exists():
            sys.exit(f"Falta el fichero estático: {src}")
        shutil.copy2(src, OUT / name)

    if (ROOT / "media").is_dir():
        shutil.copytree(ROOT / "media", OUT / "media", dirs_exist_ok=True)

    print(f"OK: sitio generado en {OUT}")
    for warning in WARNINGS:
        print(f"AVISO: {warning}")


if __name__ == "__main__":
    try:
        main()
    except KeyError as exc:
        sys.exit(f"Falta un campo en content/*.yml: {exc}")
