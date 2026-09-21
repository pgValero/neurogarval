# AGENTS.md

Single-page marketing site for NeuroGarval (Spanish psychology practice). No build, no package manager, no tests, no CI.

## Layout & deploy

- `index.html` — the site markup (HTML + JSON-LD only); no inline `<style>`/`<script>`; do not introduce a framework, bundler, or external build step.
- `styles.css` — all site CSS (extracted from the former inline `<style>` block), linked in `<head>`.
- `script.js` — all site JS (extracted from the former inline `<script>` block); classic (non-module) script at the end of `<body>` so inline `onclick` handlers and top-level `config`/functions stay global.
- `firma.html` — standalone email signature (not linked from the site); uses absolute `https://neurogarval.es/...` asset URLs.
- `CNAME` — `neurogarval.es`; host is GitHub Pages, so **pushing to `main` deploys production**.
- Static assets (`logo.svg`, `favicon.svg`, images, `aviso_legal.pdf`, `tarjeta.pdf`) are referenced by relative path.

## Conventions

- All user-facing copy is **Spanish**. Write edits in Spanish; commit messages are in Spanish too.
- Contact data is defined once in the `config` object at the top of `script.js` (line 1) and injected into `.neuro-phone`, `.neuro-mail`, `.neuro-address`, etc. by `initData()` on `DOMContentLoaded`. To change contact info, edit `config` — not the individual elements.
- Contact details are **duplicated** in the JSON-LD `<script type="application/ld+json">` block (phone, address) and in `firma.html`. Update those too or they drift.
- Service cards open a native `<dialog id="serviceModal">`; modal copy lives in the `serviceInfo` JS object (not in the card HTML). The "blog" section and the `sala-N.jpg` gallery images are placeholders awaiting real content/assets.

## Verifying

- Lint with the pre-commit hooks: `prek run --all-files` (HTMLHint for HTML, Stylelint for CSS, ESLint for JS, Lychee for links). Then open `index.html` in a browser and check the affected section (`#inicio`, `#servicios`, `#modalidades`, `#proceso`, `#especialista`, `#galeria`, `#blog`, `#faq`, `#contacto`), a service modal, and the mobile menu.
- `index.html` (~500 lines), `styles.css` (~845 lines) and `script.js` (~90 lines); prefer targeted `Edit` calls over `Write`.
