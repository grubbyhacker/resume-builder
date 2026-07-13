# Personal Agent Instructions

- When making technical decisions, do not give much weight to development cost. Prefer quality, simplicity, robustness, scalability, and long-term maintainability.
- Never open draft PRs. When changes are validated, open PRs ready for review unless Roger explicitly requests draft mode.
- Branch protection is enabled for `main`. Never commit or push directly to `main`; create a feature branch for all repository changes.
- Before committing, pushing, or opening a PR for changes that can affect generated resume artifacts, run `mise run check-office-docker` and inspect every PNG in the artifact-specific directory under `output/office-render/`. Check for clipping, overlapping text, broken glyphs, inconsistent margins or alignment, awkward page breaks, and sparse trailing pages; report the visual findings to Roger.
- Never merge, create release-triggering commits, or otherwise publish resume artifacts until Roger has reviewed the rendered DOCX/PDF output and explicitly approved the visual result.
