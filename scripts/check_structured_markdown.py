#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from build_metadata import default_artifact_path
from check_parse import check_yaml_content_present, load_resume


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
        errors.extend(check_yaml_content_present(text, resume))
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
