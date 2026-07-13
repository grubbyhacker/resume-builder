#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from build_metadata import default_artifact_path
from check_parse import check_yaml_content_present, load_resume
from render_structured_markdown import structured_role_heading


def check_structured_role_headings(text: str, resume: dict) -> list[str]:
    errors: list[str] = []
    lines = [line.strip() for line in text.splitlines()]
    cursor = 0

    for job_index, job in enumerate(resume.get("experience", [])):
        if not isinstance(job, dict):
            continue
        legacy_heading = f"### {job.get('company')} - {job.get('location')}"
        if legacy_heading in lines:
            errors.append(
                f"experience[{job_index}] uses a shared employer heading; every role must be a flat entry"
            )
        for role_index, role in enumerate(job.get("roles", [])):
            if not isinstance(role, dict):
                continue
            try:
                expected = f"### {structured_role_heading(job, role)}"
            except KeyError as exc:
                errors.append(
                    f"experience[{job_index}].roles[{role_index}] is missing key needed for heading: {exc}"
                )
                continue
            try:
                found = lines.index(expected, cursor)
            except ValueError:
                errors.append(
                    f"complete structured Markdown role heading missing for "
                    f"experience[{job_index}].roles[{role_index}]: {expected!r}"
                )
                continue
            cursor = found + 1

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check structure-preserving Markdown content.")
    parser.add_argument("--resume", type=Path, default=Path("resume.yaml"))
    parser.add_argument("--markdown", type=Path, default=None)
    args = parser.parse_args()

    try:
        markdown_path = args.markdown or default_artifact_path(args.resume, Path("output"), None, ".structured.md")
        text = markdown_path.read_text(encoding="utf-8")
        resume = load_resume(args.resume)
        errors = []
        errors.extend(check_yaml_content_present(text, resume, display_dates=False))
        errors.extend(check_structured_role_headings(text, resume))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Structured Markdown check error: {exc}", file=sys.stderr)
        return 1

    if errors:
        print(f"Structured Markdown checks failed for {markdown_path}:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"Structured Markdown checks passed for {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
