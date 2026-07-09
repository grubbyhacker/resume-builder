# Resume Builder

Minimal YAML-based resume build pipeline for ATS-safe Markdown and DOCX resumes.

## Edit the Resume

Edit `resume.yaml` as the source of truth. Keep content structured under profile, headline, summary, skills, optional projects, experience, and education.

Claude and Codex should edit `resume.yaml` only. Do not edit generated files in `output/`; they are disposable build artifacts.

## Install

```sh
mise install
mise exec -- uv sync
```

## Render

```sh
make render
```

This validates `resume.yaml` and renders:

- `output/ats.md` from `templates/ats.md.j2`
- `output/First_Last_YYYYMMDD.md` as the agent-readable Markdown filename
- `output/ats.docx` directly from YAML
- `output/First_Last_YYYYMMDD.docx` as the upload-ready DOCX filename

The DOCX renderer is intentionally direct YAML-to-DOCX. It does not convert Markdown through Pandoc.
The build date is UTC and can be overridden for reproducible builds:

```sh
RESUME_BUILD_DATE=20260708 make docx
```

To render only the DOCX:

```sh
make docx
```

To render the upload-ready PDF as well, use an environment with LibreOffice:

```sh
make pdf
```

This writes both `output/ats.pdf` and `output/First_Last_YYYYMMDD.pdf`.

## Run Checks

```sh
make check
```

The check target validates the YAML, renders Markdown, and runs parser-regression checks from `tests/expected/ats_text_expectations.yaml`.
It also renders and checks the DOCX for source-content fidelity, role/bullet placement, and ATS-hostile structures such as tables, images, and text boxes.
Apache Tika extraction is run through Docker by `make check` when Docker is available; it does not install Java or Tika on the host.

To run only DOCX checks after rendering:

```sh
make check-docx
```

To run only the Tika extraction check:

```sh
make check-tika
```

Tika approximates the text-extraction step many parsers start with. It does not model a specific ATS's field mapping; site-specific parser behavior belongs in `tests/ats_quirks.yaml` and live import validation.

To check that resume URLs are reachable:

```sh
make check-urls
```

URL checks use network access and can be affected by bot blocking. HTTP 2xx/3xx pass; common blocked-but-real responses like 401, 403, and 429 are treated as reachable. Hard failures such as DNS errors, TLS errors, timeouts, 404, and 410 fail the check.

## Office Render Checks

`make check` does not require LibreOffice. It is the fast content and structure gate.

For higher-fidelity DOCX verification, run:

```sh
make check-office
```

That target renders `output/ats.docx` through LibreOffice, inspects the resulting PDF with Poppler, checks PDF text against `resume.yaml`, checks page count, and writes render artifacts to `output/office-render/`.

LibreOffice is intentionally not a host dependency. Use one of these paths:

- Open the repo in the dev container, then run `make check-office`.
- Run `mise run check-office-docker` to build/use a local Docker image with LibreOffice and Poppler.
- Let GitHub Actions run the `office-render` job on push and pull request.

The Docker/devcontainer image installs `libreoffice-writer`, `poppler-utils`, and `fonts-liberation`. The generated PDF, text extraction, and page PNGs stay under ignored `output/`.

## Releases

On pushes to `main`, GitHub Actions runs the normal checks, the LibreOffice render checks, then creates a versioned release.

Release tags use the same UTC build date as the upload artifacts:

- Tag: `vYYYY.MM.DD`
- Markdown asset: `First_Last_YYYYMMDD.md`
- DOCX asset: `First_Last_YYYYMMDD.docx`
- PDF asset: `First_Last_YYYYMMDD.pdf`

Release notes are generated from commits. The generated files stay disposable locally under `output/`; GitHub Releases are the durable distribution point.

## ATS Quirks

Observed parser failures live in `tests/ats_quirks.yaml`. Each entry records the symptom, where it was observed, the suspected root cause, the workaround, and the guard that keeps the workaround from regressing.

When a new ATS bug appears:

1. Capture evidence, ideally a screenshot or copied parser output from the target ATS.
2. Add an entry to `tests/ats_quirks.yaml`.
3. Add or update the guard in `tests/expected/ats_text_expectations.yaml`, `scripts/check_parse.py`, or `scripts/check_docx.py`.
4. Run `make check`.

Some guards intentionally preserve ugly output if that output survives ATS import more reliably. The registry is where that tradeoff is documented.

## Clean

```sh
make clean
```

Generated output is ignored by Git.
