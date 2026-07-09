# Resume Builder

A small, deliberately over-engineered resume build pipeline.

The goal is not to make a pretty resume editor. The goal is to keep one structured source of truth, generate boring ATS-safe artifacts from it, and prevent known parser failures from sneaking back in. This exists because Applicant Tracking Systems can mangle otherwise reasonable resumes: bullets become numbered lists, custom headings turn into phantom jobs, and content after the last role gets swallowed into the wrong work-history entry.

This repo treats those failures as software bugs. The resume is data, the renderers are build steps, and parser quirks become regression tests.

## What It Builds

`resume.yaml` is the source of truth. From that file, the pipeline renders:

- `output/First_Last_YYYYMMDD.md`: a plain ATS Markdown resume.
- `output/First_Last_YYYYMMDD.structured.md`: an agent-readable structured Markdown projection of the YAML.
- `output/First_Last_YYYYMMDD.docx`: the upload-ready Word document.
- `output/First_Last_YYYYMMDD.pdf`: the PDF produced from the DOCX through LibreOffice.

The generated filenames are the same names used for release artifacts. There is no separate `ats.*` copy. The date stamp is UTC and can be overridden with `RESUME_BUILD_DATE=YYYYMMDD` for reproducible builds.

Generated files live under `output/` and are ignored by Git.

## Design Choices

- YAML is the editable source of truth.
- JSON Schema keeps the content model strict and catches typos.
- Jinja renders plain Markdown for ATS-safe text checks.
- DOCX is rendered directly from YAML with `python-docx`; Markdown is not converted through Pandoc.
- Bullets are literal `•\t` paragraphs, not Word list styles, because some ATS imports convert Word list bullets into repeated `1.` entries.
- LibreOffice and Apache Tika run in containers or CI paths so the local machine does not need Java or LibreOffice installed.
- Parser workarounds are documented in `tests/ats_quirks.yaml` and guarded by checks.

Some of these choices are intentionally unglamorous. The priority is predictable parser extraction, not document-design cleverness.

## Repository Layout

- `resume.yaml`: source resume content.
- `schema/resume.schema.json`: JSON Schema for the YAML model.
- `templates/ats.md.j2`: Markdown template.
- `scripts/render_markdown.py`: YAML to ATS Markdown.
- `scripts/render_structured_markdown.py`: YAML to structured agent Markdown.
- `scripts/render_docx.py`: YAML to DOCX.
- `scripts/build_pdf.py`: DOCX to PDF through LibreOffice.
- `scripts/check_parse.py`: Markdown parser-regression checks.
- `scripts/check_docx.py`: DOCX structure and content checks.
- `scripts/check_tika.py`: Apache Tika extraction check.
- `scripts/check_office.py`: LibreOffice/PDF render check.
- `tests/expected/ats_text_expectations.yaml`: data-driven text expectations.
- `tests/ats_quirks.yaml`: observed ATS failures and their guards.

## Editing

Edit `resume.yaml`, not generated files.

The main content sections are:

- `profile`
- `headline`
- `summary`
- `skills`
- `projects`
- `experience`
- `education`

Experience roles may have a `description`, `bullets`, or both. Use `description` for paragraph-style role summaries and `bullets` for distinct achievements that should render as bullets.

Agents should edit YAML only unless they are changing the pipeline itself. Generated files in `output/` are disposable build artifacts.

## Setup

This repo uses `mise` to bootstrap tools and `uv` to manage Python dependencies.

```sh
mise install
mise exec -- uv sync
```

## Render

Render Markdown, structured Markdown, and DOCX:

```sh
make render
```

Render the PDF as well:

```sh
make pdf
```

Render with a fixed build date:

```sh
RESUME_BUILD_DATE=20260708 make pdf
```

The DOCX build stamps the build identifier into core document properties so a copied artifact can be traced back to its build.

## Checks

Run the main validation and parser checks:

```sh
make check
```

This target:

- validates `resume.yaml` against the schema
- renders Markdown, structured Markdown, and DOCX
- checks Markdown for required strings, forbidden strings, ordering, email detection, and ATS-hostile syntax
- checks that YAML content survives rendering
- checks that role descriptions and bullets stay inside the correct role block
- checks DOCX structure for tables, images, text boxes, Word numbering, and non-standard section headings
- runs Apache Tika extraction through Docker when Docker is available

Run URL checks separately:

```sh
make check-urls
```

URL checks use network access and may be affected by bot blocking. HTTP 2xx/3xx pass; common blocked-but-real responses such as 401, 403, and 429 are treated as reachable. Hard failures such as DNS errors, TLS errors, timeouts, 404, and 410 fail.

## Office Render Checks

`make check` intentionally does not require LibreOffice on the host.

For higher-fidelity DOCX/PDF verification, run the Office checks in Docker:

```sh
mise run check-office-docker
```

That builds or reuses a local Docker image with LibreOffice, Poppler, Python, uv, and mise. The image preinstalls the pinned mise tools and Python dependencies during `docker build`, so normal reruns use Docker's layer cache instead of downloading Python and uv inside a disposable container.

Inside the container it runs:

```sh
make check-office
```

The Office check renders the named DOCX artifact through LibreOffice, inspects the resulting PDF with Poppler, checks extracted PDF text against `resume.yaml`, checks page count, and writes page render artifacts to `output/office-render/`.

You can also run `make check-office` directly inside a dev container or CI environment that already has LibreOffice and Poppler.

## Releases

On pushes to `main`, GitHub Actions runs checks, runs the Office render job, and creates a GitHub Release.

Release assets:

- `First_Last_YYYYMMDD.md`
- `First_Last_YYYYMMDD.structured.md`
- `First_Last_YYYYMMDD.docx`
- `First_Last_YYYYMMDD.pdf`

Release tags use the build date plus short commit SHA:

```text
vYYYY.MM.DD-sha
```

The SHA keeps same-day builds immutable. Release notes are generated from commits.

This repo should not be pushed to `main` until the rendered DOCX/PDF output has been visually reviewed and approved.

## ATS Quirks

Observed parser failures live in `tests/ats_quirks.yaml`.

Each entry records:

- symptom
- where it was observed
- suspected root cause
- workaround
- guard that enforces the workaround
- status or residual risk when needed

When a new ATS bug appears:

1. Capture evidence, ideally a screenshot or copied parser output.
2. Add an entry to `tests/ats_quirks.yaml`.
3. Add or update the guard in `tests/expected/ats_text_expectations.yaml`, `scripts/check_parse.py`, or `scripts/check_docx.py`.
4. Run `make check`.
5. Validate against a real import before declaring the workaround closed.

The registry is where deliberate ugliness is justified. If a workaround makes the document less elegant but more reliably parsed, it belongs there with a test.

## Clean

```sh
make clean
```

This removes generated output.
