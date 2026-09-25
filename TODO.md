# TODO

1. Clean up the CMS forms so everything is consistent and understandable.
2. Have the AI do a general review.
3. Outside the code (I cannot do it myself): optimised Google Business profile (categories, reviews, photos), profiles on Doctoralia/Top Doctors/COP Madrid, and registration in Google Search Console and Bing Webmaster Tools.

Items 1 and 2 of the original list are covered by the review below (item 9 of the first
list is the CMS cleanup; the whole review is item 2). Item 3 is still open and is the one
that brings clients: the site is only the last step of the local funnel, the Google Business
profile, the directories and the reviews are what put it in front of people.

---

## Deep review (2026-09-25): top 10 things to improve

Scope: content and conversion, SEO and structured data, accessibility and usability of the
page, usability of Pages CMS for the non-technical editor, and the repository for
developers. Verified against the **published** site (`https://neurogarval.es/`, which is
still the old `main` build), the generated `_site/`, `content/*.yml`, `.pages.yml`,
`scripts/build.py`, the legal PDF and the email signature, plus a comparison with what other
neuropsychology practices in Valdemoro and south Madrid publish.

Short version: the engineering is in very good shape and the copy is warm, honest and free
of hype. What is missing is (a) publishing what is already built, (b) the commercial
information a patient looks for before booking (hours, prices, what a first visit is),
(c) more than one URL to rank, and (d) the trust signals (credentials, photos, reviews) that
this sector depends on.

### 1. Publish the site that is already built, and finish the one-off GitHub settings

`main` still serves the old flat site: two `<title>` tags, `<link rel="canonical">` pointing
to `https://www.neurogarval.es/` (a URL that 301-redirects to the apex, so the canonical
points to a redirect) and no `robots.txt`, no `sitemap.xml` and no `llms*.txt` (all 404).
Everything built on `develop` (the JSON-LD graph, the sitemap, robots, the WebP pipeline,
the FAQ, the LLM files) is therefore invisible to search engines and to users.

Do this first, it is one pull request:

- Open the `develop` → `main` pull request by hand (the branch protection that requires
  `Build Validation / build-validation` cannot be enabled before `main` has the workflows),
  let it go green and merge it.
- Then, once: `Settings → Pages → Source: GitHub Actions`; branch protection on `main`
  (require PR + the `Build Validation / build-validation` check); auto-merge with rebase
  enabled; confirm `develop` is the branch opened in Pages CMS.
- Check that the scheduled `check_site.yml` is actually running: right now it must be red
  (it verifies `robots.txt`, `sitemap.xml` and `llms*.txt`, and the scheduled run reads
  `src/CNAME` from `main`). A red monitoring job is a good thing to notice now, not later.
- After the deploy, submit the sitemap in Google Search Console and Bing Webmaster Tools,
  verify the canonical and the `www` → apex redirect, and re-check the old `/firma.html` URL
  (renamed to `/signature.html`) with a redirect or a link.

### 2. Add the commercial information a patient needs before booking: hours, prices, conditions and service area

The site says nothing about **when** the practice is open, **how much** a session costs,
**how long** an evaluation takes, what happens if you cannot attend, how to pay, or whether
it works for an insurance/mutua referral. In this sector that is the main reason a visitor
leaves. Every comparable practice publishes it: the Doctoralia profiles in Valdemoro show
prices ("55–80 € por sesión", "evaluación neuropsicológica desde 100 €") and review counts;
other Madrid centres have a full "Tarifas" page and "Horarios de atención L-V 9-21h".

The content model already supports it, this is a new `content/horarios.yml` (or
`precios.yml`) plus a `@foreach` block, a `SPECIALS` entry for the JSON-LD and a few
paragraphs in the FAQ:

- Opening hours by day, with the exceptions (holidays, summer), visible in the contact
  section and as `openingHoursSpecification` in the JSON-LD (it is what keeps the site
  consistent with the Google Business profile).
- `First visit` block: duration, price of the first (free) consultation, what the evaluation
  consists of, how long it takes, whether a written report is delivered, and how to prepare
  a child (sleep the night before, medication as usual, school reports at hand).
- Prices or an honest orientation ("la primera es gratuita, a partir de …, …
  bonificación por bloques"), cancellation policy, payment methods (tarjeta, Bizum,
  factura) and whether private insurance or mutuas are accepted.
- Service area as visible text (Valdemoro, Pinto, Parla, Ciempozuelos, San Martín de la
  Vega, Getafe, Aranjuez, Seseña + "online en toda España") and the travel conditions for
  "a domicilio" (municipios, coste, radio), as `serviceArea` in the structured data.
- New FAQ entries with the questions patients actually ask: "¿desde qué edad?", "¿hacéis
  informes para la escuela o para adaptaciones curriculares?", "¿se puede pedir baja
  médica?", "¿trabajáis con families adoptivas/divorciadas?", "¿atendéis en inglés?",
  "¿cuánto tardáis en dar la primera cita?", "¿y si no puedo ir?".

### 3. Stop putting everything in modals: give the services and the articles their own indexable URLs

Everything is on a single URL. The two blog posts cannot be shared, linked in a WhatsApp
message, ranked, or shown in Google Images, and the `BlogPosting` nodes are incomplete (no
`datePublished`, both point to `#blog`). There is no way to compete for "evaluación
neuropsicológica en niños Valdemoro", "TDAH Madrid" or "rehabilitación cognitiva tras ictus",
which is where the organic traffic of this profession actually comes from.

`build.py` already loops over the YAML, so this is a new template plus a render step, not a
redesign:

- `src/page.html` + a `render_pages()` step that writes one page per service (and per
  modality, per article) with its own `<title>`, `<meta description>`, canonical, H1 and
  `Article`/`Service` JSON-LD; links from the home page cards to the real URL, keeping the
  modal only as a progressive enhancement (or dropping it).
- `date`, `slug` and `tags` fields for the posts, plus a `content/posts/` collection in
  `.pages.yml` (the skeleton is already there, commented out at the end) and one blog index
  page.
- The sitemap then lists real pages with `lastmod`, and `llms*.txt` can link to the article
  URLs instead of `#blog`.

Until that exists, the effort spent on `llms.txt` is not paying for itself: 2026 data shows
that the large majority of `llms.txt` files receive zero crawler requests and Google states
that no new machine-readable file is needed for AI search. Keep it (it is cheap and it is
generated), stop investing in it, and spend that time on indexable pages.

### 4. Build the trust layer that the sector runs on: credentials, profiles, real photos and reviews

The information that proves she is a professional exists, but it is in the legal PDF and not
on the site: *Máster en Psicología General Sanitaria*, member of the *Colegio Oficial de la
Psicología de Madrid*, NIF, regulated activity. The About section is four warm paragraphs
with no verifiable fact. For a regulated health profession, that is where the conversion
gap is.

- Credentials as structured content (`specialist.yml` or a new "Credenciales" block):
  degree, college and collegiate number, years of experience, languages, specific
  training in neurodevelopmental disorders, the fact that a **written report** is delivered
  and who may attend the sessions (with the consent of the patient).
- Explicit scope: she does not prescribe medication, she works from a referral (pediatra,
  neuropediatra, neurologist) and explains what happens without one, and what she does and
  does not treat. This kind of clarity is a strong E-E-A-T signal and reduces bad-fit
  appointments.
- "A quién ayudo" section with real profiles: niños y adolescentes, adultos, mayores,
  familias; and by problem: TDAH, TEA, dificultades de aprendizaje, deterioro cognitivo,
  daño cerebral, ansiedad y estrés, dificultades conductuales. Right now those words only
  appear inside service modals.
- Real photos of the clinic. There are six empty slots in the "Atención en Clínica" gallery
  and the build renders them as six blue tiles with a camera icon
  (`_site/index.html`, `modality_gallery()` in `scripts/build.py`): a visitor sees an
  unfinished page. Either upload the photos or make `modality_gallery()` skip empty
  entries. Photos of the space are one of the strongest trust elements for a home-based
  practice, and they also feed the Google Business profile.
- Reviews: ask the first patients for a Google review and surface them (a small
  "Lo que dicen" block with consent, and a link to the Google profile). Review volume is
  the main local ranking factor and it is the one thing the site cannot do alone.
- A short, visible note that the practice is not an emergency service, with the 024
  (Suicide Prevention) line. It is what a responsible mental-health site does.

### 5. Give the page a single, obvious call to action

The hero has two buttons (WhatsApp and the phone number) and a "primera consulta gratuita"
box, but the header, the footer and the mobile menu have no booking action at all. The
desktop menu is also missing "Proceso", which the mobile menu has
(`src/index.html`: 8 links in the overlay, 7 in the header).

- Add a "Pedir cita" button in the header (desktop and mobile menu) and in the footer,
  pointing to the contact section or straight to a prefilled WhatsApp message
  (`https://wa.me/34711233888?text=Hola%2C%20me%20gustar%C3%ADa%20informarme...`), which
  costs nothing, needs no backend and no cookies, and is the preferred channel of most
  patients in Spain.
- Keep the phone visible as text, but make the WhatsApp message prefilled per section
  (consulta, evaluación, cita) so the first exchange is already useful.
- Add the "descargar contacto" (`neurogarval.vcf`) and the already existing but unused
  `media/qr.svg` to the contact section and to the email signature.

### 6. Fix the concrete SEO and data bugs that are in the code today

Small, verifiable defects, all in one pull request:

- The `BlogPosting` images in the JSON-LD point to `media/*.png`, which is **not published**
  (only the WebP version is): `jsonld_graph()` uses `media_url()` and never consults
  `WEBP_SUBSTUTES`, unlike `render_sitemap_image()`. Two 404 URLs inside the structured
  data of every page.
- `geo` in the JSON-LD is parsed with a regex from the Maps embed URL
  (`maps_coordinates()`), while `clinic_info.site.geo_position` already holds exactly the
  same coordinates. Two sources of truth for one fact: if the editor pastes a different
  embed, the coordinates silently change or disappear. Use `geo_position` and validate the
  embed with a `pattern` instead.
- `priceRange: "$"` on a practice that charges in euros.
- The `<title>` is 65 characters and will be truncated in the results; "Neuropsicóloga en
  Valdemoro" should be at the front, and the description could include the problems treated
  (TDAH, TEA, aprendizaje) instead of only the phone number.
- The `<h1>` ("Evaluación e intervención personalizada") and the section `<h2>`s
  ("Compromiso con tu salud mental", "Publicaciones") contain no service, no place and no
  entity name. The badge above the `<h1>` is the only place where the profession appears.
- `sitemap.xml` lists `llms.txt` and `llms-full.txt` as pages (they are not HTML pages) and
  has no `lastmod`; `changefreq` and `priority` have been ignored by Google for years.
- `llms.txt` and `llms-full.txt` print the address as "C/ Diego de Almagro, 32, 28342,
  Valdemoro, Madrid" (list joined with commas) instead of " - ".
- `keyword` meta with 20 entries (including the abbreviation and the full form of the same
  ones) has no value for Google; keep it only for Bing, or drop it.
- Document in the README that **FAQ rich results no longer exist**: Google stopped showing
  them on 7 May 2026 and removed the support in the Search Console API in August 2026, so
  the `FAQPage` node stays as machine-readable content for assistants, not as a SERP
  feature. The README currently implies the opposite.

### 7. Close the legal gaps that a Spanish health site has today

Not code, but it is the part that can cost money, and it is half done:

- There is no "Política de privacidad" and no "Política de cookies", although the legal
  notice links to a cookie policy that does not exist, and the site embeds Google Maps,
  which sets cookies. Either a click-to-load map facade (or a static map image plus a "ver
  en Google Maps" link) and the two policy pages, or a clear "we do not use cookies"
  statement.
- The site loads **Montserrat from fonts.googleapis.com**. Loading fonts from Google's CDN
  transfers the visitor's IP to a third country, which the AEPD has sanctioned in Spain.
  Montserrat is licensed for self-hosting: download the WOFF2 files, serve them from the
  repository, and preconnect only to the same origin. The same applies to the Bootstrap
  Icons CDN, which can be replaced by the SVG dictionary that `build.py` already has.
- In `media/aviso_legal.pdf` the field "N.º Colegiado:" is **empty**. LSSI art. 5 requires
  the registration number of a regulated profession, and it is the number the rest of the
  site displays. The same document names `www.neurogarval.es` while the site is the apex
  domain, and mangles the name of the Colegio de la Psicología de Madrid.
- `content/signature.yml` (the only file an editor can change in the signature) announces
  data processing "para enviarle comunicaciones comerciales" and gives a different email
  address (`garciavaleroteresa@gmail.com` instead of `teresa@neurogarval.es`), plus two
  typos ("noes", "elimínelo"). The footer of every email contradicts the site.
- The footer has no link to the privacy policy or the cookie policy, and `tarjeta.pdf` (a
  business card published at the root) and `media/qr.svg` are published but referenced
  nowhere.

### 8. Fix the front-end: accessibility, navigation and weight

The page is static and fast, but there are real defects with no content involved:

- With a fixed 80 px header and no `scroll-margin-top` on the sections, every menu link
  lands with the title of the section hidden under the bar. One line in `styles.css`.
- The mobile menu button has no accessible name (it only contains `<i class="bi bi-list">`),
  no `aria-expanded` and no `aria-controls`; the overlay is always in the DOM, so its eight
  links are focusable while the menu is closed; and Escape does not close it. Use the
  native `<dialog>` that is already used for the modals, or add the ARIA state and the key.
- The blog cards are `role="button" tabindex="0"` but have no `:focus-visible` outline
  (only `.service-card` and `.modality-item` do, `styles.css`).
- Headings jump from `h2` to `h4` in four sections (modalidades, proceso, blog, contacto).
- No `prefers-reduced-motion` block, although there is a global `scroll-behavior: smooth`
  and a 0.5 s menu transition.
- The hero image is `display: none` below 768 px: the main trust visual disappears exactly
  where most of the traffic is. The WebP is 77 KB, which is affordable on mobile data.
- No responsive images: no `srcset`, no `sizes`, and `photo.webp` is 1096×1394 (123 KB) for
  a slot of about 500 px. `prepare_media()` could generate 400/800/1200 px variants from
  the same Pillow pass that already exists, plus a `preload` for the LCP image.
- Third-party render-blocking requests: Google Fonts and the Bootstrap Icons CSS.

### 9. Finish the Pages CMS experience for the editor

The architecture is right (one file per section, Markdown, uploads, validation patterns),
but the form is still noisy and the guidance is missing in places:

- The three read-only collections (`common.yml`, `clinic_info.yml`, `footer.yml`) are shown
  as forms with dozens of greyed-out fields, and `clinic_info.yml` alone is a wall of 60
  inputs. The cleanest fix is to split the **type registry** from the **CMS schema**: keep
  the declarations in a `types:` key of `.pages.yml` that `load_pages_types()` also reads,
  and leave the read-only files out of `content:`, so they do not appear in the editor at
  all. Nothing in the site would change.
- Add a `description` to each editable collection (what the section is for, how long the
  texts should be, where they appear) and to the few fields that have none.
- `map_embed` is a free-text URL pasted from Google: add a `pattern` that validates the
  `https://www.google.com/maps/embed?...` shape, and better, ask only for the place and let
  the build assemble the URL.
- `process.steps`, `services.items` and `blog.posts` have no `min`, so a click can empty a
  section; `clinic_info.structured_data` is a `boolean` that controls nothing (the marker
  always renders) and is a trap for whoever reads `.pages.yml` next.
- Image guidance: recommended dimensions (hero 786×766, blog covers 1200×675 16:9), maximum
  weight, and "always write the alt text". A phone photo at 4000 px produces a 500 KB PNG
  and a 250 KB WebP; a warning in the build when an image exceeds a threshold would catch
  it.
- The `signature` collection is the only place where the editor can break the legal texts,
  and those two read-only paragraphs are the biggest thing on the form; the collection also
  does not explain that the signature is published at `/signature.html`.
- Clean up the noise in the generated HTML comments: the big block at the top of
  `src/index.html` ends up in the published page, and the "Deja vacío" hints in the YAML
  end up as visible text next to the contact data (`<!-- +34 711 233 888 -->`).

### 10. Repository: tests, pinned dependencies, and documentation that matches reality

The README is unusually good for a project of this size, but a few claims have drifted and
the project has no safety net for the refactor it plans:

- No unit tests for `build.py`. The README says the build *is* the test suite, which is true
  for the templates and the content, but `expand_loop`, `fill_contact`, `jsonld_graph`,
  `plain_text`, `image_size` and `webp_size` are pure functions with no assertions, and
  splitting the file into modules (the pending refactor) would be blind. A
  `tests/test_build.py` with 20 assertions on those functions is enough.
- Dependencies are unpinned: CI runs `pip install pyyaml markdown pillow prek`. A
  `pyproject.toml` (or `requirements.txt` + `requirements-dev.txt`) with the working
  versions, plus `uv` for local runs, makes the build reproducible.
- No linting of the YAML: a `check-yaml`/`yamllint` hook would cover `content/*.yml` and
  `.pages.yml`, which are the files the editor writes.
- No validation of the generated structured data: a step that parses the JSON-LD, checks
  that every `@id` is unique, that every URL it references is actually published and that
  every `BlogPosting` has `datePublished` would have caught item 6.
- Stale numbers in the documentation: README says `build.py` has "~1.180 lines" (1.236),
  "four linters" (there are nine hooks) and "~85 lines of JS" (86). The figure in
  `Feature overview` about safety is the one that misleads most, because the project is
  stronger than the doc says.
- Housekeeping: no `LICENSE` (README says so explicitly), no `CHANGELOG.md`, and
  `tarjeta.pdf` and `media/qr.svg` are published although nothing links to them.

---

## New functionalities (ranked by usefulness for this use case)

The use case is narrow and worth optimising for: one professional who has to sell sessions,
publish content once a month without a developer, on a cheap static site that must not
collect data from patients. Every item below respects that: no server, no database, no
tracking, and everything editable from Pages CMS.

### 1. Request-appointment form with a prefilled WhatsApp fallback

A short form (name, contact, age of the patient, reason for consultation, preferred
modality, availability) that either opens a prefilled WhatsApp message or posts to a
serverless endpoint (Formspree, Cloudflare Worker, `mailto:` fallback). The reason for
consultation is the field that lets her triage before the first call, and it gives her data
to write the blog ("lo que más me preguntan") and to spot demand for a new service.
Needs the privacy policy of item 7 of the first list; a consent checkbox and a link are
enough, and no cookie banner is required if nothing is stored in the browser.

### 2. Booking link to a real agenda

A "See availability and book" button pointing to her Google Calendar appointment schedules
(or Cal.com). Zero code, zero maintenance, and it removes the reason a patient gives for
not calling: "I don't want to bother her with a call". The free first consultation can be
a 20-minute slot, and the site can show her real availability instead of a promise.

### 3. Editorial calendar and idea bank inside the CMS

The real bottleneck for a small practice is not publishing code, it is not knowing what to
write. A `content/ideas.yml` with the topic, the target keyword, the notes, and whether it
is published, gives the owner 20-30 ideas to start from, and the build can drop an
"upcoming" line or a `relatedPosts` block into the blog. It is the cheapest way to make the
blog grow from 2 posts to 20 without touching a template.

### 4. Clinic photo gallery with a lightbox

Photos of the rooms, the entrance (for the street number) and the materials used in an
evaluation, uploaded from the CMS, converted to WebP by the build, with a click-to-enlarge
lightbox that is a `<dialog>` like the existing ones. Photos of the space are what a parent
looks for before taking a child to an unknown professional, and they can be reused in the
Google Business profile and in Instagram.

### 5. "Your first visit" page and printable summaries

A dedicated page (or a section) that tells the patient what the first visit is like step by
step, what to bring, how to prepare a child, how long it takes, what the report contains and
what it does not (a neuropsychological evaluation does not diagnose, it describes cognitive
functioning). Plus a one-page PDF summary (generated from the same YAML as a printable
service sheet) for parents who take it to the paediatrician. Both reduce no-shows and
objections, and both can be handed out at the clinic.

### 6. Contact assets: vCard, QR and the business card that is already in the repository

`media/qr.svg` and `media/tarjeta.pdf` are in the repository and published but unused. The
build can generate `_site/neurogarval.vcf` (name, role, collegiate number, phone, WhatsApp,
email, website, address, Instagram) from `common.yml` and `signature.yml`, and the site
and the email signature can link to it (and show the QR). "Download contact" in one tap is
how a patient turns into a recurring session, and it makes the signature and the site agree
on a single source of truth.

### 7. Content and SEO quality gate inside the build

A `python scripts/build.py --check` (run in the same workflow, before publishing) that fails
or warns about what a human does not see: `<title>` and description lengths, exactly one
`h1`, missing `alt`, a H1 without the service or the locality, images over a weight or
dimension threshold, links to anchors that no longer exist, blog posts without a date,
`datePublished` missing, duplicate paragraphs, an `area_served` that is not visible in the
page, and JSON-LD that references an image that is not published. It fits the existing
"fail fast" philosophy and turns the review items into a permanent guard instead of a
one-off list.

### 8. Preview environment for the editor

Deploy `develop` to a second GitHub Pages site (`neurogarval-preview.pages.dev` or a
`/preview/` folder) on every push to `develop`, and mention the URL in the description of
the publish action in `.pages.yml`. The owner sees the result of an edit before pressing
"Publish changes", which removes the fear of publishing a mistake to the public, and it is
about 20 lines in the workflows (the build job is already reusable).

### 9. Privacy-friendly measurement

Today there is no way to know whether the WhatsApp button, the phone, the first consultation
or the blog bring patients. Cloudflare Web Analytics (or a self-hosted Plausible) is
cookieless, does not need a consent banner, does not set identifiers and gives the two
numbers that matter: clicks on the contact actions and traffic per section. If the practice
sits in Spain, this must stay inside the "no personal data to third parties" line the site
currently advertises.

### 10. External profiles as first-class content, and a resources area

A `profiles.yml` (Doctoralia, Top Doctors, Colegio Oficial de la Psicología de Madrid,
other directories) that feeds the `sameAs` of the JSON-LD, the footer and a small "Where to
find me" block, so the entity signals grow as the profiles do. With it, a "Resources"
section: downloadable guides (how to request a neuropsychological evaluation, how to
prepare school adaptations, a glossary of tests), each one an indexable page and a reason for
a family to write, plus a link from each resource to the contact section. When there is
capacity, the same content model can add a small events section for talks in schools and
associations in Valdemoro, and a second language for the international families in the
southern Madrid municipalities (the marker system is language-agnostic; it would mean
duplicated content files and `hreflang`).

### Considered and left out of the top 10

A/B testing of titles (needs an analytics tool and one visit too many per version),
a newsletter (the CMS cannot send it; Instagram and WhatsApp already do the job of staying
in touch), a PWA or offline support (not useful for a one-page site), and a
`humans.txt` (the information is already in the legal notice and the About section).
