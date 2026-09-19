# AGENTS.md

Single-page marketing site for NeuroGarval (Spanish psychology practice). No build, no package manager, no tests, no CI.

## Layout & deploy

- `index.html` — the entire site: HTML + inline `<style>` + inline `<script>`. Self-contained; do not introduce a framework, bundler, or external build step.
- `firma.html` — standalone email signature (not linked from the site); uses absolute `https://neurogarval.es/...` asset URLs.
- `CNAME` — `neurogarval.es`; host is GitHub Pages, so **pushing to `main` deploys production**.
- Static assets (`logo.svg`, `favicon.svg`, images, `aviso_legal.pdf`, `tarjeta.pdf`) are referenced by relative path.

## Conventions

- All user-facing copy is **Spanish**. Write edits in Spanish; commit messages are in Spanish too.
- Contact data is defined once in the `config` object near the end of `index.html` (~line 1285) and injected into `.neuro-phone`, `.neuro-mail`, `.neuro-address`, etc. by `initData()` on `DOMContentLoaded`. To change contact info, edit `config` — not the individual elements.
- Contact details are **duplicated** in the JSON-LD `<script type="application/ld+json">` block (phone, address) and in `firma.html`. Update those too or they drift.
- Service cards open a native `<dialog id="serviceModal">`; modal copy lives in the `serviceInfo` JS object (not in the card HTML). The "blog" section and the `sala-N.jpg` gallery images are placeholders awaiting real content/assets.

## Verifying

- There is nothing to lint/test/build. Open `index.html` in a browser and check the affected section (`#inicio`, `#servicios`, `#modalidades`, `#proceso`, `#especialista`, `#galeria`, `#blog`, `#faq`, `#contacto`), a service modal, and the mobile menu.
- `index.html` is ~1350 lines with one large `<style>` block; prefer targeted `Edit` calls over `Write`.
