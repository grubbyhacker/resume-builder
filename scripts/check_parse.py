#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
TABLE_RE = re.compile(r"^\s*\|.+\|\s*$", re.MULTILINE)
IMAGE_RE = re.compile(r"!\[[^\]]*]\([^)]*\)")
HTML_BLOCK_RE = re.compile(r"^\s*</?[A-Za-z][^>]*>\s*$", re.MULTILINE)


def load_expectations(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the document root")
    return data


def as_string_list(value: object, key: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"expectations field '{key}' must be a list of strings")
    return value


def check_required_exact(text: str, expected: list[str]) -> list[str]:
    return [f"missing required string: {item!r}" for item in expected if item not in text]


def check_order(text: str, expected: list[str]) -> list[str]:
    errors: list[str] = []
    cursor = -1
    for item in expected:
        found = text.find(item, cursor + 1)
        if found == -1:
            errors.append(f"ordered string not found after offset {cursor}: {item!r}")
            continue
        cursor = found
    return errors


def check_forbidden(text: str, forbidden: list[str]) -> list[str]:
    return [f"forbidden string found: {item!r}" for item in forbidden if item in text]


def check_ats_text(text: str, expectations: dict) -> list[str]:
    errors: list[str] = []
    errors.extend(check_required_exact(text, as_string_list(expectations.get("required_exact"), "required_exact")))
    errors.extend(check_order(text, as_string_list(expectations.get("required_order"), "required_order")))
    errors.extend(check_forbidden(text, as_string_list(expectations.get("forbidden"), "forbidden")))

    if expectations.get("require_email", True) and not EMAIL_RE.search(text):
        errors.append("no email address detected")
    if expectations.get("forbid_tables", True) and TABLE_RE.search(text):
        errors.append("obvious Markdown table syntax detected")
    if expectations.get("forbid_images", True) and IMAGE_RE.search(text):
        errors.append("Markdown image syntax detected")
    if expectations.get("forbid_html_blocks", True) and HTML_BLOCK_RE.search(text):
        errors.append("HTML block syntax detected")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run data-driven parser-regression checks against ATS Markdown.")
    parser.add_argument("--markdown", type=Path, default=Path("output/ats.md"))
    parser.add_argument("--expectations", type=Path, default=Path("tests/expected/ats_text_expectations.yaml"))
    args = parser.parse_args()

    try:
        text = args.markdown.read_text(encoding="utf-8")
        expectations = load_expectations(args.expectations)
        errors = check_ats_text(text, expectations)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Parse check error: {exc}", file=sys.stderr)
        return 1

    if errors:
        print(f"Parser checks failed for {args.markdown}:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"Parser checks passed for {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
