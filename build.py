#!/usr/bin/env python3
"""build.py — generador del sitio estático neurogarval.es.

Qué hace
--------
1. Lee el contenido editable de Pages CMS: content/*.yml (un fichero por
   sección más common.yml, footer.yml y firma.yml) y el registro de tipos
   .pages.yml.
2. Recorre las plantillas src/index.html y src/firma.html sustituyendo los
   marcadores __archivo.ruta.campo__ (p. ej. __hero.badge__,
   __servicios.items.0.title__ o __common.contact.phone__) por el contenido
   de cada fichero. La ruta se resuelve en el YAML del archivo indicado; el
   tipo del campo se lee de .pages.yml y decide cómo se renderiza:
     - rich-text (Markdown)  -> se convierte a HTML
     - image                 -> ruta normalizada media/...
     - component icono       -> HTML del icono (ICONS)
     - lista de cadenas      -> se une con <br>
     - el resto              -> texto plano escapado
   Si un marcador no se encuentra en el contenido o su campo no está
   registrado en .pages.yml, el build falla indicando exactamente qué campo
   se buscó y en qué plantilla.
3. Escribe el contacto de content/common.yml (fuente única) directamente en
   el index.html generado: los huecos .neuro-* (teléfono, WhatsApp, email,
   dirección y Maps) quedan resueltos sin JavaScript.
4. Escribe el contenido completo de servicios, modalidades y artículos en el
   propio HTML (bloques .card-full ocultos); script.js lo copia a los modales.
5. Copia los estáticos (CSS, JS, CNAME, favicon, logo y PDFs) y las imágenes
   de media/ a _site/, manteniendo la estructura pública actual.

Uso
---
    pip install pyyaml markdown  # dependencias del generador
    python build.py              # genera ./_site
    # Sin pip (p. ej. entorno aislado):
    uv run --with pyyaml --with markdown python build.py

La GitHub Action (.github/workflows/deploy.yml) hace exactamente esto en
cada push a main y publica _site/ en GitHub Pages. No hay framework ni
generador de sitio: solo este script.

Marcadores
----------
Formato: __archivo.ruta.campo__ (el primer segmento es el nombre del fichero
de content/, p. ej. __servicios.items.0.title__). Los índices numéricos
recorren listas. Si el archivo, la ruta o el campo no existen en
content/*.yml o el campo no está declarado en .pages.yml, se lanza
CampoAusenteError con el nombre del campo buscado.

Listas repetidas
----------------
Las tarjetas e ítems de las listas (servicios, modalidades, pasos del proceso,
artículos del blog y preguntas frecuentes) no se escriben en la plantilla
índice a índice: se envuelven en un bloque de plantilla que build.py repite
una vez por elemento del YAML, por lo que añadir o quitar entradas en el CMS
no exige tocar el HTML. Ver expand_loops() para la sintaxis (@foreach).
"""

from __future__ import annotations

import html
import re
import shutil
import sys
from fnmatch import fnmatch
from pathlib import Path

try:
    import markdown
    import yaml
except ImportError as exc:  # pragma: no cover
    missing = "Markdown" if exc.name == "markdown" else "PyYAML"
    sys.exit(f"Falta {missing}. Instálalo con:  pip install pyyaml markdown")

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
CONTENT = ROOT / "content"
OUT = ROOT / "_site"

# Plantillas que procesa build.py: (clave para mensajes, ruta al fichero).
TEMPLATES = {
    "src/index.html": SRC / "index.html",
    "src/firma.html": SRC / "firma.html",
}

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
    # Iconos de fuente Bootstrap Icons (incluida en src/index.html)
    "building": '<i class="bi bi-building"></i>',
    "laptop": '<i class="bi bi-laptop"></i>',
    "house": '<i class="bi bi-house-door"></i>',
    "journal": '<i class="bi bi-journal-text"></i>',
}

# Ficheros estáticos que se copian a _site/. Los recursos que antes estaban
# en la raíz se leen ahora desde media/, pero se publican en la raíz para
# conservar las rutas públicas existentes (favicon, PDFs y logo).
STATIC_FILES = [
    (SRC / "styles.css", "styles.css"),
    (SRC / "script.js", "script.js"),
    (ROOT / "CNAME", "CNAME"),
    # SEO y LLM: ficheros fijos (no se generan desde content/*.yml; si cambia
    # el contenido del CMS, actualizar llms.txt y llms-full.txt a mano).
    (SRC / "robots.txt", "robots.txt"),
    (SRC / "sitemap.xml", "sitemap.xml"),
    (SRC / "llms.txt", "llms.txt"),
    (SRC / "llms-full.txt", "llms-full.txt"),
    (ROOT / "media/favicon.svg", "favicon.svg"),
    (ROOT / "media/logo.svg", "logo.svg"),
    (ROOT / "media/aviso_legal.pdf", "aviso_legal.pdf"),
    (ROOT / "media/tarjeta.pdf", "tarjeta.pdf"),
]
MEDIA_EXCLUDES = ("favicon.svg", "logo.svg", "aviso_legal.pdf", "tarjeta.pdf")

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

    Los campos declarados como rich-text en .pages.yml pasan por aquí; el
    resto de campos (títulos, botones, metadatos) siguen usando ``esc``.
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


def raw_phone(phone: str) -> str:
    """Teléfono sin espacios/paréntesis/giones para enlaces tel: y wa.me."""
    return re.sub(r"[\s()\-]", "", phone)


# ---------------------------------------------------------------------------
# Resolución de marcadores __archivo.ruta.campo__
# ---------------------------------------------------------------------------
# Formato: primer segmento = fichero de content/ (sin .yml), el resto es la
# ruta dentro del YAML (los números recorren listas).
PLACEHOLDER_RE = re.compile(r"__(?P<ref>[a-z0-9]+(?:\.[a-z0-9_]+)+)__")


class CampoAusenteError(Exception):
    """Campo referenciado en una plantilla que no se encuentra ni en el
    contenido (content/*.yml) ni en el registro de tipos (.pages.yml).

    El build aborta mostrando qué campo se buscó, en qué plantilla y por qué
    no se encontró.
    """

    def __init__(self, plantilla: str, ruta: str, motivo: str):
        self.plantilla = plantilla
        self.ruta = ruta
        self.motivo = motivo
        super().__init__(
            f"Campo no encontrado: {ruta} (plantilla {plantilla}) — {motivo}."
        )


# Campos derivados: no existen en content/*.yml ni en .pages.yml; los calcula
# build.py a partir de otros campos (p. ej. __common.contact.phone_tel__ en la
# firma de email). Estos marcadores no pasan por el registro de .pages.yml.
DERIVED_FIELDS = frozenset({"common.contact.phone_tel"})


def resolve_data(plantilla: str, ref: str, file: str, route: list[str],
                 context: dict) -> tuple:
    """Busca el valor de un marcador en el YAML cargado.

    Devuelve (valor, contenedor): el valor del campo y el nodo que lo
    contiene (para los renderizadores especiales que necesitan datos
    hermanos, p. ej. el alt de una miniatura).
    """
    data = context.get(file)
    if data is None:
        raise CampoAusenteError(
            plantilla, ref,
            f"no existe content/{file}.yml (revisa el nombre del archivo)")
    node = data
    parent = data
    for seg in route:
        parent = node
        if seg.isdigit():
            if not isinstance(node, (list, tuple)):
                raise CampoAusenteError(
                    plantilla, ref,
                    f"'{seg}' no es un índice de lista en content/{file}.yml")
            idx = int(seg)
            if idx >= len(node):
                raise CampoAusenteError(
                    plantilla, ref,
                    f"el índice {idx} supera las {len(node)} entradas de "
                    f"content/{file}.yml")
            node = node[idx]
        else:
            if not isinstance(node, dict) or seg not in node:
                raise CampoAusenteError(
                    plantilla, ref,
                    f"no existe '{'.'.join(route)}' en content/{file}.yml")
            node = node[seg]
    return node, parent


# ---------------------------------------------------------------------------
# Bucles de plantilla (@foreach) — listas que se repiten solas
# ---------------------------------------------------------------------------
# Las tarjetas e ítems de las listas (servicios, modalidades, pasos del
# proceso, artículos del blog y preguntas frecuentes) NO se escriben en la
# plantilla índice a índice: se envuelven en un bloque @foreach que build.py
# repite una vez por elemento del YAML, de modo que añadir o quitar entradas
# en el CMS no exige tocar el HTML.
#
# Sintaxis en la plantilla:
#
#   <!-- @foreach:servicios.items -->
#   <div class="service-card" data-service="__servicios.items.n.id__"
#        onclick="openServiceModal('__servicios.items.n.id__')">
#       <h3>__servicios.items.n.title__</h3>
#       ...
#   </div>
#   <!-- @endforeach:servicios.items -->
#
# Dentro del bloque, el segmento "n" del marcador se sustituye por el índice
# del elemento actual (0, 1, 2...); el resto del marcador se resuelve igual
# que siempre. Los marcadores __loop.index__ y __loop.index0__ valen la
# posición (1-based y 0-based) y sirven para, p. ej., el número del paso o el
# índice del modal (openModalityModal(index)). Los marcadores de la sección
# que no dependen del elemento (p. ej. __servicios.more_label__) se dejan
# intactos. Si la lista queda vacía, el bloque no genera nada. Los bucles no
# se anidan.
LOOP_TOKENS = re.compile(
    r"<!--\s*@(?P<open>foreach:(?P<ref>[a-z0-9_]+(?:\.[a-z0-9_]+)+)|"
    r"endforeach(?::(?P<close_ref>[a-z0-9_]+(?:\.[a-z0-9_]+)+))?)\s*-->"
)


def expand_loop(plantilla: str, ref: str, body: str, items: list) -> str:
    """Repite el cuerpo del bloque una vez por elemento de la lista."""
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
    return "\n".join(fragments)


def expand_loops(plantilla: str, source: str, context: dict) -> str:
    """Localiza los bloques @foreach de la plantilla y los expande."""
    parts = []
    stack: list[str] = []
    pos = 0
    for m in LOOP_TOKENS.finditer(source):
        token = m.group("open")
        if token.startswith("foreach:"):
            ref = m.group("ref")
            if stack:
                sys.exit(f"{plantilla}: @foreach anidado ('{ref}' dentro de "
                         f"'{stack[-1]}') no soportado")
            parts.append(source[pos:m.start()])
            pos = m.end()
            stack.append(ref)
        else:
            if not stack:
                sys.exit(f"{plantilla}: cierre @endforeach sin @foreach previo")
            ref = stack.pop()
            close_ref = m.group("close_ref")
            if close_ref and close_ref != ref:
                sys.exit(f"{plantilla}: @endforeach cierra '{close_ref}' pero "
                         f"el @foreach abrió '{ref}'")
            body = source[pos:m.start()]
            file, _, route_str = ref.partition(".")
            node, _ = resolve_data(plantilla, ref, file, route_str.split("."),
                                   context)
            if not isinstance(node, (list, tuple)):
                raise CampoAusenteError(
                    plantilla, ref,
                    f"'{ref}' no es una lista en content/{file}.yml "
                    "(un @foreach solo repite sobre listas)")
            parts.append(expand_loop(plantilla, ref, body, node))
            pos = m.end()
    if stack:
        sys.exit(f"{plantilla}: @foreach '{stack[-1]}' sin @endforeach")
    parts.append(source[pos:])
    return "".join(parts)


def resolve_type(plantilla: str, ref: str, file: str, route: list[str],
                 fields_by_file: dict) -> dict:
    """Busca el campo en el registro de tipos (.pages.yml).

    Devuelve la definición del campo (type, component, list...). Si el campo
    no está declarado, el build falla: es un error de configuración.
    """
    fields = fields_by_file.get(file)
    if fields is None:
        raise CampoAusenteError(
            plantilla, ref,
            f"no existe la colección '{file}' en .pages.yml (¿la has añadido "
            "al registro de tipos?)")
    node = fields
    for i, seg in enumerate(route):
        if seg.isdigit():
            continue  # índice de lista: el tipo está en los subcampos
        field = next((f for f in node if f.get("name") == seg), None)
        if field is None:
            raise CampoAusenteError(
                plantilla, ref,
                f"el campo '{seg}' no está declarado en .pages.yml "
                f"(colección '{file}': {', '.join(f.get('name') or '?' for f in node)})")
        if i == len(route) - 1:
            return field
        sub = field.get("fields")
        if not sub:
            raise CampoAusenteError(
                plantilla, ref,
                f"el campo '{seg}' de .pages.yml no tiene subcampos para "
                f"sostener la ruta '{ref}'")
        node = sub
    raise CampoAusenteError(plantilla, ref, "ruta vacía en .pages.yml")


def render_field(value, field: dict) -> str:
    """Renderiza un valor según el tipo declarado en .pages.yml."""
    if field.get("component") == "icono":
        return icon_html(value)
    if field.get("type") == "rich-text":
        return markdown_html(value)
    if field.get("type") == "image":
        return media_url(value)
    if isinstance(value, list):
        return "<br>".join(esc(v) for v in value)
    return esc(value)


# ---------------------------------------------------------------------------
# Renderizadores especiales (casos que un tipo de .pages.yml no puede
# expresar solo). Clave de plantilla -> ruta exacta o patrón con "*" ->
# función (valor, contenedor) -> HTML.
# ---------------------------------------------------------------------------
def render_modalities(value, parent: dict) -> str:
    """Hero: une las modalidades con "·" y protege la última de partirse."""
    parts = [p.strip() for p in str(value).split("·")]
    if len(parts) > 1:
        head = " · ".join(esc(p) for p in parts[:-1])
        return (f'{head} <span style="white-space: nowrap;">'
                f"· {esc(parts[-1])}</span>")
    return esc(parts[0])


def render_modality_content(value, parent: dict) -> str:
    """Modalidad: Markdown del contenido + galería de fotos de la consulta."""
    content = markdown_html(value)
    gallery = modality_gallery(parent.get("images") or [])
    return f"{content}\n{gallery}" if gallery else content


def render_blog_thumb(value, parent: dict) -> str:
    """Miniatura del blog: <img> con la foto o icono de reserva si no hay."""
    src = media_url(value)
    if not src:
        return icon_html("journal")
    return f'<img src="{esc(src)}" alt="{esc(parent.get("title"))}" loading="lazy">'


SPECIALS: dict[str, dict] = {
    "src/index.html": {
        "hero.modalities": render_modalities,
        "blog.posts.*.image": render_blog_thumb,
        # Contenido completo de la modalidad: Markdown + fotos de la consulta
        # (opcionales: solo las modalidades que las declaran las incluyen).
        "modalidades.items.*.modal_content": render_modality_content,
    },
    "src/firma.html": {
        # La firma muestra la dirección en una sola línea.
        "common.contact.address_lines": lambda v, parent: " - ".join(
            esc(line) for line in v),
    },
}


def apply_template(template_key: str, source: str, context: dict,
                   fields_by_file: dict) -> str:
    """Sustituye los marcadores __archivo.ruta.campo__ de una plantilla."""
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
    """Índice .pages.yml -> {nombre de colección: lista de campos}."""
    path = ROOT / ".pages.yml"
    if not path.exists():
        sys.exit(f"Falta el registro de tipos: {path}")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    content = (cfg or {}).get("content")
    if not isinstance(content, list):
        sys.exit(f"{path}: no se encuentra la lista 'content'.")
    return {col["name"]: col.get("fields") or []
            for col in content if col.get("name")}


# ---------------------------------------------------------------------------
# Contacto — content/common.yml -> huecos .neuro-* del index.html generado.
# Fuente única: el contacto se escribe aquí, en el HTML; script.js no lo
# toca (su único trabajo con datos es rellenar los modales de servicios y
# modalidades). Los enlaces tel:/wa.me de la firma usan la clave derivada
# __common.contact.phone_tel__ (ver DERIVED_FIELDS).
# ---------------------------------------------------------------------------
def fill_contact(doc: str, contact: dict) -> str:
    """Resuelve en el HTML todos los huecos .neuro-* de la plantilla.

    Atributos: href de teléfono/WhatsApp/email/Maps.
    Texto:     teléfono, email y dirección. Hero, sección de contacto y
               footer salen todos del mismo common.yml.
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
# Modales: su contenido completo se escribe en el HTML (bloques .card-full
# ocultos de cada tarjeta) para que buscadores y asistentes de IA lo lean sin
# JavaScript; script.js solo lo copia al modal. Los servicios se abren por su
# campo "id" (openServiceModal('neuro') busca data-service="neuro"), así que
# debe existir y ser único.
# ---------------------------------------------------------------------------
def validate_service_ids(c: dict) -> None:
    seen: set[str] = set()
    for item in c["servicios"]["items"]:
        sid = item.get("id")
        if not sid:
            sys.exit("Un servicio de content/servicios.yml no tiene 'id'. "
                     "Es obligatorio: abre su modal (openServiceModal('id')).")
        if sid in seen:
            sys.exit(f"Identificador duplicado en content/servicios.yml: "
                     f"'{sid}'. Debe ser único por servicio.")
        seen.add(sid)


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
            + "\n".join(f"    {f}" for f in figures)
            + "\n</div>")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build_context() -> dict:
    """Carga content/*.yml y añade los campos derivados (DERIVED_FIELDS)."""
    context = {p.stem: load_yaml(p.stem) for p in sorted(CONTENT.glob("*.yml"))}
    contact = context["common"]["contact"]
    contact["phone_tel"] = f"tel:{raw_phone(contact['phone'])}"
    return context


def main() -> None:
    context = build_context()
    validate_service_ids(context)
    fields_by_file = load_pages_types()

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    for key, path in TEMPLATES.items():
        source = path.read_text(encoding="utf-8")
        doc = apply_template(key, source, context, fields_by_file)
        if key == "src/index.html":
            doc = fill_contact(doc, context["common"]["contact"])
        (OUT / path.name).write_text(doc, encoding="utf-8")


    for src, name in STATIC_FILES:
        if not src.exists():
            sys.exit(f"Falta el fichero estático: {src}")
        shutil.copy2(src, OUT / name)

    if (ROOT / "media").is_dir():
        shutil.copytree(
            ROOT / "media",
            OUT / "media",
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(*MEDIA_EXCLUDES),
        )

    print(f"OK: sitio generado en {OUT}")
    for warning in WARNINGS:
        print(f"AVISO: {warning}")


if __name__ == "__main__":
    try:
        main()
    except CampoAusenteError as exc:
        sys.exit(str(exc))