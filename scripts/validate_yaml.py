#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker


def load_yaml(path: Path) -> object:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def format_error(error) -> str:
    location = ".".join(str(part) for part in error.absolute_path)
    prefix = location if location else "<root>"
    return f"{prefix}: {error.message}"


def validate(resume_path: Path, schema_path: Path) -> int:
    resume = load_yaml(resume_path)
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(resume), key=lambda item: list(item.absolute_path))

    if errors:
        print(f"Validation failed for {resume_path}:", file=sys.stderr)
        for error in errors:
            print(f"  - {format_error(error)}", file=sys.stderr)
        return 1

    print(f"Validated {resume_path} against {schema_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate resume YAML against the JSON Schema.")
    parser.add_argument("--resume", type=Path, default=Path("resume.yaml"))
    parser.add_argument("--schema", type=Path, default=Path("schema/resume.schema.json"))
    args = parser.parse_args()

    try:
        return validate(args.resume, args.schema)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
