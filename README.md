# Resume Builder

Minimal YAML-based resume build pipeline for an ATS-safe Markdown resume.

## Edit the Resume

Edit `resume.yaml` as the source of truth. Keep content structured under profile, headline, summary, skills, experience, education, and optional writing/publications.

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

This validates `resume.yaml` and renders `output/ats.md` from `templates/ats.md.j2`.

## Run Checks

```sh
make check
```

The check target validates the YAML, renders Markdown, and runs parser-regression checks from `tests/expected/ats_text_expectations.yaml`.

## Clean

```sh
make clean
```

Generated output is ignored by Git.
