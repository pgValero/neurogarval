# NeuroGarval

**Landing page for NeuroGarval, a neuropsychology and health psychology practice in Valdemoro (Madrid, Spain).**

Live site: [neurogarval.es](https://neurogarval.es)

This repository is the production site for that business: hero, services, care modalities
(in-clinic / online / home visits), process, about the specialist, blog, FAQ, contact
section with an embedded map, footer, and a standalone email signature template.

---

# The project behind the site

> The rest of this document is not about the business. It describes the reusable project
> behind the site: why it is built this way, how it works, and what it gives to owners,
> maintainers, visitors and search engines. It is a reference for any small business,
> professional practice or local service that wants the same setup.

## Table of contents

- [Why it exists](#why-it-exists)
- [Feature overview](#feature-overview)
- [Architecture](#architecture)
- [Quality gates](#quality-gates)
- [Tech stack](#tech-stack)
- [Design principles and conventions](#design-principles-and-conventions)

## Why it exists

A solo professional practice needs five things. Each one maps to a property of this setup.

### 📝 Update without a developer, without breaking anything

The owner edits copy, prices, photos, FAQ and blog posts in a browser form. Saving only
commits YAML on `main` and triggers nothing; **"Deploy Page"** builds and validates
first, so a bad edit never reaches production.

### ⚡ Fast and cheap

Static HTML plus one CSS file and one small JavaScript file. $0 hosting on GitHub Pages,
no database, no server, no maintenance windows.

### 🔍 Rank well and be easy to quote

Title, description, keywords, canonical URL, geo and social tags, `sitemap.xml`, JSON-LD
graph and `llms.txt` / `llms-full.txt` generated from the same content, always fresh for
search engines and AI assistants.

### 🔐 Fully owned

Content is YAML in Git, not rows in a proprietary builder. Every change has an author,
a date and a reviewable diff, and the site keeps working even if every third-party
service disappears.

### 🔄 Consistent everywhere

Phone, WhatsApp, email, address and Maps link are edited once in `content/common.yml`
and written into the HTML, the JSON-LD and the signature. Sections can never disagree,
and crawlers need no JavaScript to see the contact data.

### 🛠️ For the maintainer

No framework to upgrade, no lockfile drift, almost no supply-chain surface. Content and
structural changes are separated, most updates touch a single YAML file, and the build is
deterministic — a complete site or a loud failure.

### 👥 For visitors

Fast first paint, no client-side rendering, readable with JavaScript disabled, keyboard
and screen-reader accessible modals, light WebP images, no trackers or cookie banner.

## Feature overview

| Area | What it does |
| --- | --- |
| Editing | Friendly web CMS with one file per page section, Markdown support, image uploads and Spanish labels |
| Generation | One Python script resolves markers, expands loops, converts Markdown, generates JSON-LD and writes `_site/` |
| Front-end | Semantic HTML5, one hand-written CSS file, ~85 lines of vanilla JS for modals and the mobile menu |
| SEO and AI | Canonical URL, geo tags, social cards, sitemap with images, JSON-LD graph, `llms.txt` and crawler-friendly `robots.txt` |
| Images | Automatic PNG/JPEG to WebP conversion at build time, with dimensions and lazy loading |
| Safety | Fail-fast build, linters on the generated site, live-site smoke test |
| Publishing | Save to `main` (triggers nothing), then **"Publicar cambios"** builds, validates and deploys |
| Cost | $0 hosting on GitHub Pages; CMS and domain are the only costs |

## Architecture

One question drives the whole system: *how does a non-technical owner change the website?*
Content is data in Git, GitHub turns a commit into a validated build, and the build output
is the live page. Nobody edits HTML and nothing ships without passing the build.

```mermaid
flowchart LR
    Edit["Edit<br/>Pages CMS form in the browser"] --> Repo["Repository<br/>content YAML + templates on main"]
    Repo --> Build["Build<br/>build.py + linters"]
    Build --> Live["Live<br/>static _site/ on GitHub Pages"]
```

| Question | Answer given by the architecture |
| --- | --- |
| *What does the editor touch?* | Only `content/*.yml` and `media/` through a form. No HTML, no code, no local tools. |
| *Where is the truth?* | In Git. Every change is a commit with an author, a date and a reviewable diff. |
| *What stops a typo from reaching production?* | The build fails on any missing field and the linters check the generated site; on failure the live site keeps the previous version. |
| *What is actually deployed?* | Only the build output, uploaded as an artifact. Templates and YAML never ship. |

Templates hold structure with `__file.path.field__` markers and `@foreach` loop blocks;
`scripts/build.py` reads the field type from `.pages.yml`, renders each value accordingly
and repeats each loop block once per YAML element, so adding a service, modality, process
step, blog post or FAQ question needs zero HTML changes. The domain comes from `src/CNAME`;
every other fixed value (identity, SEO, social, menu labels, schema texts) comes from
`content/clinic_info.yml`. See `AGENTS.md` for the marker, loop, contact and media details.

## Quality gates

| Gate | What it catches |
| --- | --- |
| `build.py` | Missing/misspelled content fields, undeclared types, duplicate service ids, missing static files |
| **HTMLHint** | Malformed tags, duplicated attributes, non-lowercase tag names, duplicate ids |
| **Stylelint** | CSS errors, unknown properties, bad syntax |
| **ESLint** | JavaScript problems |
| **Lychee** | Broken local and external links in the HTML (skips `tel:` links and template markers) |
| **zizmor** | GitHub Actions security: unpinned actions, excessive permissions, credential persistence, template injection |
| **ShellCheck** | Bugs and portability problems in `scripts/check_site.sh` |
| **ruff** | Lint and format of `scripts/build.py` (pyflakes, bugbear, pyupgrade, import order...) |
| **markdownlint-cli2** | Markdown structure: broken anchors, missing code-fence language, heading levels, list and spacing rules |
| `check_site.sh` | Live site unreachable, empty, unresolved `__markers__`, missing `<title>`, missing canonical URL, no visible text, missing image, missing `robots.txt` / `sitemap.xml` / `llms*.txt` / logo / favicon |

`_site/` is gitignored, so CI stages it (`git add -f _site`) before running the linters —
the checks run against the **generated** site, not just the sources.

## Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| Front-end | Hand-written HTML5, CSS and vanilla JS | Zero dependencies, nothing to patch, works forever |
| Styling | One `styles.css` with CSS custom properties, Montserrat (Google Fonts) and Bootstrap Icons from CDN | No build step for CSS, design tokens in one place |
| Modals | Native `<dialog>` + `<details>` | Accessibility and behavior without a library |
| Content | YAML, one file per section | Human-readable, diff-friendly, framework-free |
| CMS | Pages CMS (`.pages.yml`) | Git-based, no vendor lock-in, free tier, per-field descriptions for the editor |
| Templating | Custom marker + `@foreach` engine in `build.py` | ~200 lines instead of a template engine dependency |
| Markdown | Python-Markdown (`extra`) | Editors write prose, the build renders HTML |
| Images | Pillow | WebP conversion at build time |
| Hosting | GitHub Pages | Free, HTTPS, versioned, globally cached |
| CI/CD | GitHub Actions (2 workflows) | Free, validation before deploy, manual + button deploy, scheduled checks |
| Hooks | `prek` (pre-commit compatible) with HTMLHint, Stylelint, ESLint, Lychee, zizmor, ShellCheck, ruff and markdownlint | Runs the same checks locally and in CI |
| Validation | Bash + `curl` | Live smoke test with no dependencies |

## Design principles and conventions

- **Content and presentation are separated.** Templates hold structure; YAML holds
  values; the build joins them.
- **Every site-specific literal is in content, not in code.** The domain comes from
  `src/CNAME`; identity, SEO, social tags, menu labels and structured-data texts come
  from `clinic_info.yml`. Code contains only markup, classes, icon names and
  schema.org vocabulary.
- **One source of truth per fact.** Contact details, keywords, service catalogue,
  FAQ, posts — each lives in exactly one place and is reused everywhere.
- **Fail fast, never silently.** Unresolved content is a build error, not a broken page.
- **Progressive enhancement.** Full content is in the HTML; JavaScript only enhances it.
- **No hardcoded copies of lists.** Loops, not repeated markup.
- **Content files stay machine-clean.** Exactly the format the CMS writes: no YAML
  comments, no blank lines between fields. Editor guidance lives in the `description`
  of each field in `.pages.yml`.
- **Do not introduce a framework or bundler.** That is the whole point of the project.

## License

MIT — see [LICENSE](LICENSE). You may fork the code, templates and content,
use them commercially and modify them, as long as the copyright notice and
permission notice stay included.
