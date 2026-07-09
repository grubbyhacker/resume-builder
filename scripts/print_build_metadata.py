#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from build_metadata import build_date, build_identifier, build_sha, load_resume, named_artifact_path, release_tag


def main() -> int:
    parser = argparse.ArgumentParser(description="Print resume build metadata for shell/CI use.")
    parser.add_argument("--resume", type=Path, default=Path("resume.yaml"))
    parser.add_argument("--date", default=None, help="UTC build date override in YYYYMMDD form")
    parser.add_argument("--build-sha", default=None, help="Short or full commit SHA for traceable release tags")
    args = parser.parse_args()

    try:
        resume = load_resume(args.resume)
        date_string = build_date(args.date)
        sha = build_sha(args.build_sha)
        markdown = named_artifact_path(Path("output"), resume, date_string, ".md", args.resume)
        structured_markdown = named_artifact_path(Path("output"), resume, date_string, ".structured.md", args.resume)
        docx = named_artifact_path(Path("output"), resume, date_string, ".docx", args.resume)
        pdf = named_artifact_path(Path("output"), resume, date_string, ".pdf", args.resume)
        print(f"build_date={date_string}")
        print(f"build_identifier={build_identifier(date_string, sha)}")
        print(f"release_tag={release_tag(date_string, sha)}")
        print(f"markdown_asset={markdown}")
        print(f"structured_markdown_asset={structured_markdown}")
        print(f"docx_asset={docx}")
        print(f"pdf_asset={pdf}")
        return 0
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Metadata error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
