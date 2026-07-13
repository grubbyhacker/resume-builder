# Resume Builder

A small, deliberately over-engineered resume build pipeline.

The resume is treated as a declarative software artifact: YAML is the source of truth, renderers are build steps, parser failures are regressions, and reviewed binaries are release assets. The goal is not to build a visual resume editor. The goal is to produce predictable, ATS-safe Markdown, DOCX, and PDF files while preserving evidence for why every unusual formatting decision exists.

Applicant Tracking Systems can mangle otherwise reasonable documents. Native Word bullets can become repeated `1.` entries, unfamiliar headings can become phantom jobs, later roles can lose their employer, and content after the final job can be absorbed into its description. This repository treats those failures as bugs that should be documented, reproduced, and guarded by automated checks.

## System at a Glance

```text
resume.yaml
    │
    ├── JSON Schema validation
    │
    ├── Jinja2 ───────────────► ATS Markdown
    │
    ├── Python renderer ──────► Structured Markdown
    │
    └── python-docx ──────────► DOCX
                                  │
                                  └── LibreOffice soffice ─────► PDF
                                                                    │
                                                                    ├── Poppler text/page checks
                                                                    └── Poppler PNGs + Pillow checks
```

The design follows a few simple principles:

- Keep one structured, reviewable source of truth.
- Validate before rendering.
- Generate binaries; never hand-edit them.
- Test the output through independent parsers, not only through the library that created it.
- Record real ATS failures and keep their workarounds under regression coverage.
- Separate deterministic checks from network-dependent checks and human visual review.
- Publish immutable, traceable artifacts only after validation and visual approval.

## What It Builds

`resume.yaml` is the default source. A normal build produces:

- `output/First_Last_YYYYMMDD.md`: plain ATS Markdown.
- `output/First_Last_YYYYMMDD.structured.md`: an agent-readable, structure-preserving projection.
- `output/First_Last_YYYYMMDD.docx`: the upload-ready Word document.
- `output/First_Last_YYYYMMDD.pdf`: the PDF generated from that DOCX by LibreOffice.

The UTC date can be overridden with `RESUME_BUILD_DATE=YYYYMMDD` for reproducible builds. Release builds also include the short Git commit SHA in the release tag and stamp build metadata into the DOCX core properties.

Generated artifacts live under `output/` and are ignored by Git. The files distributed in a GitHub Release are produced by the same build path used locally and in CI; there is no separately maintained release copy.

## Toolchain

The development toolchain is pinned in `mise.toml`, and Python dependencies are locked in `uv.lock`.

| Technology | Role |
| --- | --- |
| Python 3.12 | Renderers, validators, and checks |
| mise | Toolchain installation and task aliases |
| uv | Python dependency locking and execution |
| PyYAML | YAML loading |
| JSON Schema / jsonschema | Strict source-data validation |
| Jinja2 | ATS Markdown rendering |
| python-docx | Direct DOCX construction and inspection |
| LibreOffice `soffice` | Headless DOCX-to-PDF conversion |
| Apache Tika | Independent DOCX text extraction |
| Poppler | PDF metadata, text extraction, and page rendering |
| Pillow | PNG pixel-boundary analysis |
| Docker | Reproducible Tika and Office-check environments |
| GitHub Actions | Pull-request checks and release automation |

Pandoc and WeasyPrint are not used. The DOCX is generated directly from YAML with `python-docx`, and the PDF is generated from the DOCX with LibreOffice. Tika is called through its HTTP API rather than `python-tika`; Poppler is called through its CLI rather than a PDF wrapper such as `pypdf`.

## Source Model and Validation

The editable source is `resume.yaml`. Its main sections are:

- `profile`
- `headline`
- `summary`
- `skills`
- `projects`
- `experience`
- `education`

Experience roles may contain a description alone or a description followed by bullets. Descriptions render as prose paragraphs; bullets render as distinct achievements. A role with bullets must have a description so an importer cannot silently promote the first achievement into unlabeled introductory prose.

Experience dates use canonical `YYYY-MM` values, with `present` reserved for a current role. Education dates may use `YYYY` or `YYYY-MM`. Renderers convert these machine-readable values into familiar text such as `Dec 2024` and `Present`.

Before any artifact is rendered, `scripts/validate_yaml.py` loads the YAML with `PyYAML` and validates it against the Draft 2020-12 schema in `schema/resume.schema.json`. The schema:

- rejects unknown properties at the root and within modeled objects
- requires the core sections and profile fields
- rejects empty required strings and arrays
- validates email and URI formats
- requires at least one employer, role, and education record
- requires a city/state-style location for every employer
- requires every role to have a title, canonical dates, and a description
- requires roles with bullets to begin with a distinct description
- rejects start dates later than end dates
- requires roles, employers, and education records to be reverse chronological
- preserves project and education fields as separate structured values

Date ordering and range checks are semantic validation performed after the JSON Schema passes. Cross-employer date overlaps are intentionally allowed because concurrent roles can be legitimate. Validation errors include the failing path so content-model mistakes fail early instead of surfacing as malformed binaries.

## Transformations

### YAML to ATS Markdown

`scripts/render_markdown.py` renders `templates/ats.md.j2` with Jinja2. `StrictUndefined` makes missing data a build failure rather than silently emitting empty content.

The template intentionally uses plain, conservative Markdown:

- contact fields are joined with ` | `
- summary and skill items are ordinary bullets
- projects appear before work history
- only standard section headings are used
- every dated role repeats title, employer, location, and dates
- descriptions remain paragraphs and achievements remain bullets
- education follows work history as the final recognized section

The Markdown artifact is both distributable output and the simplest representation on which to run ATS regression checks. Canonical source dates are formatted for human readers at this boundary.

### YAML to Structured Markdown

`scripts/render_structured_markdown.py` creates a second Markdown projection for agents and other software. It favors explicit field identity over presentation:

- profile values have labels
- websites and bullets remain nested lists
- projects retain separate name, URL, and description fields
- employers contain nested roles
- company, location, dates, description, and bullets remain distinct
- education retains separate institution, location, degree, field, and date values

This artifact makes the YAML easier to consume without forcing another tool to infer structure from the upload-oriented document.

### YAML to DOCX

`scripts/render_docx.py` constructs the Word document directly with `python-docx`. Markdown is not an intermediate format.

The renderer applies:

- US Letter page dimensions
- Arial typography
- 0.65-inch top and bottom margins
- 0.7-inch left and right margins
- centered name, contact line, and headline
- standard Word heading styles with restrained spacing
- blue section headings with paragraph borders
- keep-with-next behavior on headings where practical
- separately formatted role descriptions and achievement bullets
- distinct institution and degree/field lines
- `en-US` document language metadata
- build date and optional commit SHA in core properties

Bullets are deliberately emitted as normal paragraphs beginning with the literal text `•\t`. They do not use native Word list numbering. This is less elegant internally, but it avoids an observed importer failure that converted each Word bullet into a repeated `1.` entry.

Every role heading repeats all fields an importer needs:

```text
Title, Company | City, ST | Start - End
```

That repetition prevents later roles at the same company from losing their employer or location when an ATS treats every dated role as an independent work-history entry.

### DOCX to PDF

`scripts/build_pdf.py` invokes LibreOffice directly:

```text
soffice --headless --convert-to pdf --outdir ... input.docx
```

The build fails if `soffice` is unavailable, the process exits unsuccessfully, or the expected PDF is not created. Converting the final DOCX, rather than independently rendering a PDF from YAML, keeps the two upload formats visually and semantically aligned.

## Checks

The checks are layered so that each representation is tested at the level where failures are easiest to detect.

| Layer | Primary checks |
| --- | --- |
| YAML | Schema, formats, required fields, unknown fields |
| ATS Markdown | Required and forbidden text, order, syntax, role boundaries, source losslessness |
| Structured Markdown | Source losslessness |
| DOCX object model | Tables, shapes, styles, literal bullets, standard headings |
| DOCX XML | Drawings, text boxes, tables, numbering properties |
| Tika extraction | Independent text survival and role attribution |
| PDF text | Required content, order, forbidden content, numbered-bullet regression |
| PDF pages | Page count, render count, blank pages, edge contact, bottom safety zone |
| Human review | Clipping, overlap, typography, alignment, page breaks, balance |

### Main Check Suite

Run the default suite with:

```sh
make check
```

This validates the YAML, renders Markdown, structured Markdown, and DOCX, runs the Python unit tests, checks all three artifacts, and passes the DOCX through Apache Tika when Docker is available.

### ATS Markdown Checks

`scripts/check_parse.py` combines stable policy expectations from `tests/expected/ats_text_expectations.yaml` with content and ordering checks derived from the current YAML source. Names, contact data, headlines, employers, role headings, dates, and education values do not need to be manually copied into the expectations file. It verifies:

- required exact strings
- required document and section order
- absence of forbidden placeholders, punctuation, and headings
- survival of every meaningful YAML string
- ordered role headings
- descriptions and bullets remaining inside the correct role block
- descriptions preceding their role's bullets
- bullets remaining in YAML order
- detectable email syntax
- institution-before-degree education ordering
- spelled-out degrees and a detectable `Degree in Field` line
- absence of Markdown tables, images, and standalone HTML blocks
- absence of body lines beginning with title-like nouns such as `Author`, `Executive`, `Lead`, `Manager`, or `Director`

The section-order assertion is an ATS workaround, not a stylistic preference:

```text
Summary → Skills → Projects → Professional Experience → Education
```

Skills and Projects appear before Professional Experience because some importers attach otherwise valid trailing content to the final dated role. Education is the only content after work history because it is reliably recognized as a section boundary.

### Structured Markdown Checks

`scripts/check_structured_markdown.py` verifies that every significant string in the YAML source appears in the structured projection. Its purpose is losslessness: a field added to the source should not silently disappear from the agent-readable artifact.

### DOCX Checks

`scripts/check_docx.py` inspects both the `python-docx` object model and raw `word/document.xml`.

Structural checks reject:

- Word tables
- inline shapes and drawings
- legacy pictures
- text boxes
- table XML
- Word numbering properties
- `List Bullet` paragraphs
- nonstandard section headings
- paragraph borders outside recognized section headings

It also requires:

- at least one literal bullet
- the exact `•\t` bullet prefix
- a bottom border on every standard section heading

The extracted DOCX text is then subjected to the same required-text, forbidden-text, ordering, source-losslessness, role-boundary, title-noun, and education checks used for Markdown.

### Apache Tika Checks

`scripts/check_tika_docker.sh` starts the pinned `apache/tika:3.1.0.0-full` image on a dynamically allocated localhost port. `scripts/check_tika.py` waits for readiness, uploads the DOCX with an HTTP `PUT`, and reads the raw response with Python's standard `urllib`.

The response is decoded, stripped of markup, HTML-unescaped, and whitespace-normalized. The resulting text must contain every meaningful YAML value, and descriptions and bullets must remain inside their expected role blocks.

This matters because `python-docx` is both the DOCX renderer and one of the inspectors. Tika supplies an independent parser closer to the extraction behavior used by document-processing systems.

If Docker is not installed locally, the Tika wrapper reports a skip. CI is expected to run it with Docker available.

### Unit Tests

The standard-library `unittest` suite covers date semantics, role-schema policy, and PNG analysis:

- canonical date parsing and human-readable formatting
- start/end consistency and reverse-chronological ordering
- the requirement that roles with bullets also have descriptions
- grayscale inversion and thresholding produce the expected ink bounds
- content inside the bottom safety zone fails
- artifact-specific render directories remove stale pages and legacy generic PNGs
- sparse final pages produce advisory diagnostics rather than hard failures

Unit tests are run as part of `make check`.

## Office and PDF Verification

The default suite intentionally does not require LibreOffice on the host. For the full render path, run:

```sh
mise run check-office-docker
```

The task builds or reuses `.devcontainer/office-check.Dockerfile`, which pins the base image and contains LibreOffice Writer, Poppler, Fontconfig, Liberation fonts, Python, mise, uv, and the locked project dependencies. An explicit Fontconfig rule maps Arial to Liberation Sans in Linux. The repository is mounted into the container, which runs:

```sh
make check-office
```

You can run `make check-office` directly in CI or a development environment that already has LibreOffice and Poppler installed.

### LibreOffice and Poppler Checks

`scripts/check_office.py` independently converts the DOCX into `output/office-render/`, then:

1. Uses `fc-match` to verify that Arial resolves to Arial or Liberation Sans and reports the actual mapping.
2. Uses `pdfinfo` stdout to parse the page count.
3. Fails on zero pages or more than the configured maximum of three.
4. Uses `pdftotext -layout` to create an extracted text file.
5. Repairs extraction-time word hyphenation and normalizes whitespace.
6. Reapplies required-text, ordering, forbidden-text, and YAML-losslessness checks.
7. Rejects lines resembling bullets converted into `1. text`.
8. Uses `pdftoppm` to render every page as a 144-DPI PNG.
9. Confirms that the PNG count matches `pdfinfo`.

### PNG Isolation and Pixel Checks

Each verified PDF receives its own page directory:

```text
output/office-render/First_Last_YYYYMMDD-pages/page-1.png
```

Before rendering, the directory is deleted and recreated. This prevents one resume variant from overwriting another and prevents a shorter rebuild from leaving behind a stale final page. Legacy generic `page-*.png` files are also removed.

Pillow analyzes an in-memory derivative of each untouched page image:

1. Convert the PNG to grayscale.
2. Invert it so white is zero and visible ink is positive.
3. Threshold values below 16 to ignore faint antialiasing noise.
4. Calculate the bounding box of visible ink.

The check fails if a page is blank, content touches any physical page edge, or the page has less than 0.35 inches of bottom whitespace. If the final page contains less than one inch of vertical ink, the checker emits an advisory warning for a possible orphan or sparse trailing page; it does not fail because short final sections can be intentional. The original PNG remains unchanged for manual or multimodal-agent review.

### Visual Review

Pixel and text checks cannot reliably judge every layout defect. Changes that affect rendered artifacts require inspection of every PNG for:

- clipping
- overlapping text
- broken glyphs
- inconsistent margins or alignment
- awkward page breaks
- sparse trailing pages
- overall readability and balance

The automated checks detect hazards; they do not replace final visual approval.

## Optional URL Checks

URL checks are separate because they require network access and can be affected by bot defenses:

```sh
make check-urls
```

`scripts/check_urls.py` checks LinkedIn, profile websites, and project URLs. It sends `HEAD`, falls back to `GET` for HTTP 405, validates TLS certificates, uses a ten-second timeout, and retries once by default.

HTTP 2xx and 3xx pass. Statuses commonly returned by real but protected endpoints—401, 403, 405, 429, and 999—are treated as reachable but blocked or rate-limited. Definitive HTTP failures, DNS failures, TLS errors, and timeouts fail the check.

## ATS Regression Registry

Observed parser failures live in `tests/ats_quirks.yaml`. Each entry records:

- the symptom
- where and when it was observed
- the suspected root cause
- the chosen workaround
- the automated guard
- residual risk when applicable

The current registry covers:

- native Word bullets becoming repeated numbered items
- unfamiliar headings becoming phantom jobs
- trailing sections being absorbed into the final job
- title-like first words becoming phantom job titles
- bullets being assigned to the wrong concurrent role
- later roles losing shared employer and location data
- first bullets being promoted into description text
- degree abbreviations preventing field-of-study detection
- OCR damage to em dashes and `~`

When a new ATS bug appears:

1. Capture the evidence, ideally with imported text or a screenshot.
2. Add an entry to `tests/ats_quirks.yaml`.
3. Add or update a guard in the expectations or check scripts.
4. Run `make check` and the Office checks.
5. Validate against a real import before declaring the workaround closed.

The registry is where deliberate ugliness is justified. A workaround that makes the document internally less elegant but measurably more reliable belongs here with an explanation and a test.

## CI and Releases

`.github/workflows/build.yml` runs on pull requests and pushes to `main`.

The validation job installs the pinned toolchain and runs `make check`. A separate Office job runs the shared pinned Office container and uploads `output/office-render/` even when the check fails so the rendered evidence remains available for diagnosis. Local verification, CI verification, and release rendering therefore use the same LibreOffice, Poppler, Fontconfig, and font environment.

On pushes to `main`, a release-classification job examines the changed paths. It requests a release only when files capable of changing generated resume artifacts were modified, including:

- `resume.yaml`
- schema files
- templates
- render and check scripts
- Python dependency files
- `Makefile`
- `mise.toml`
- the Office-check Dockerfile and Fontconfig rule

Documentation, agent instructions, Dependabot configuration, and workflow-only changes do not create resume releases. A release is intended to mean that the downloadable resume itself may have changed.

The release job waits for validation and Office checks, sets a UTC build date and short commit SHA, rebuilds all artifacts in the shared Office container, and publishes:

- ATS Markdown
- structured Markdown
- DOCX
- PDF

Tags use the immutable format:

```text
vYYYY.MM.DD-sha
```

Generated resume artifacts must be visually reviewed and approved before an artifact-affecting change is merged to `main`.

## Setup

Install the pinned toolchain and Python dependencies:

```sh
mise install
mise exec -- uv sync
```

The repository also includes a development container with LibreOffice, Poppler, and the required fonts.

## Common Commands

Render Markdown, structured Markdown, and DOCX:

```sh
make render
```

Render the canonical PDF as well:

```sh
make pdf
```

Run schema, parser, DOCX, Tika, and unit checks:

```sh
make check
```

Run the complete LibreOffice, Poppler, PNG, and visual-review path:

```sh
mise run check-office-docker
```

Build with a fixed date:

```sh
RESUME_BUILD_DATE=20260708 make pdf
```

Remove generated output:

```sh
make clean
```

## Tailored and Scratch Resumes

One-off variants can be built from ignored YAML files under `resumes/scratch/`:

```sh
cp resume.yaml resumes/scratch/acme-platform-director.yaml
make check RESUME=resumes/scratch/acme-platform-director.yaml
make pdf RESUME=resumes/scratch/acme-platform-director.yaml
RESUME=resumes/scratch/acme-platform-director.yaml mise run check-office-docker
```

Their artifact names include the source filename as a variant slug:

```text
output/First_Last_acme-platform-director_YYYYMMDD.docx
output/First_Last_acme-platform-director_YYYYMMDD.pdf
```

If a tailored resume becomes useful enough to preserve, move it out of `resumes/scratch/` and commit it as a tracked variant.

## Repository Layout

```text
resume.yaml                              Source resume
schema/resume.schema.json               Strict source schema
templates/ats.md.j2                     ATS Markdown template
scripts/render_markdown.py              YAML → ATS Markdown
scripts/render_structured_markdown.py   YAML → structured Markdown
scripts/render_docx.py                  YAML → DOCX
scripts/build_pdf.py                    DOCX → PDF
scripts/check_parse.py                  ATS Markdown regressions
scripts/check_structured_markdown.py    Structured Markdown losslessness
scripts/check_docx.py                   DOCX structure and text checks
scripts/check_tika.py                   Independent Tika extraction checks
scripts/check_office.py                 LibreOffice, Poppler, and PNG checks
scripts/check_urls.py                   Optional network checks
tests/expected/                         Data-driven output expectations
tests/ats_quirks.yaml                   ATS failure and workaround registry
.github/workflows/build.yml             CI and release pipeline
```

## Limits of Automation

The pipeline intentionally does not claim to automate every form of correctness:

- A real ATS import remains the final authority for parser behavior.
- Visual review remains necessary for typography, overlap, balance, and semantic page-break quality.
- Pixel checks detect edge and bottom-margin hazards, not arbitrary alignment errors.
- Sparse trailing pages produce advisory telemetry and are reviewed rather than rejected by a generic heuristic.
- URL checks are network-dependent and therefore optional.
- Tika is skipped locally when Docker is unavailable.
- There is no golden-image comparison or automated multimodal layout gate.

The objective is not to pretend documents are perfectly testable. It is to automate the failures that can be made deterministic, preserve evidence for the ones that cannot, and make every release auditable.
