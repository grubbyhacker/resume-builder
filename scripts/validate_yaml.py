#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from date_utils import ResumeDate, parse_resume_date


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


def descending_order_errors(items: list[tuple[str, tuple[ResumeDate, ResumeDate]]], label: str) -> list[str]:
    errors: list[str] = []
    for previous, current in zip(items, items[1:]):
        previous_path, previous_key = previous
        current_path, current_key = current
        if previous_key < current_key:
            errors.append(
                f"{label} must be reverse chronological: {current_path} is newer than {previous_path}"
            )
    return errors


def semantic_errors(resume: dict) -> list[str]:
    errors: list[str] = []
    employer_keys: list[tuple[str, tuple[ResumeDate, ResumeDate]]] = []

    for job_index, job in enumerate(resume["experience"]):
        role_keys: list[tuple[str, tuple[ResumeDate, ResumeDate]]] = []
        for role_index, role in enumerate(job["roles"]):
            path = f"experience[{job_index}].roles[{role_index}]"
            try:
                start = parse_resume_date(role["start"], allow_present=False)
                end = parse_resume_date(role["end"])
            except ValueError as exc:
                errors.append(f"{path}: {exc}")
                continue
            if start > end:
                errors.append(f"{path}: start date {role['start']!r} is later than end date {role['end']!r}")
            role_keys.append((path, (end, start)))
        errors.extend(descending_order_errors(role_keys, f"experience[{job_index}].roles"))
        if role_keys:
            employer_keys.append((f"experience[{job_index}]", max(key for _, key in role_keys)))

    errors.extend(descending_order_errors(employer_keys, "experience"))

    education_keys: list[tuple[str, tuple[ResumeDate, ResumeDate]]] = []
    for education_index, item in enumerate(resume["education"]):
        path = f"education[{education_index}]"
        start_value = item.get("start")
        end_value = item.get("end", start_value)
        try:
            start = parse_resume_date(start_value, allow_year=True, allow_present=False)
            end = parse_resume_date(end_value, allow_year=True, allow_present=False)
        except ValueError as exc:
            errors.append(f"{path}: {exc}")
            continue
        if start > end:
            errors.append(f"{path}: start date {start_value!r} is later than end date {end_value!r}")
        education_keys.append((path, (end, start)))
    errors.extend(descending_order_errors(education_keys, "education"))
    return errors


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

    semantic_validation_errors = semantic_errors(resume)
    if semantic_validation_errors:
        print(f"Validation failed for {resume_path}:", file=sys.stderr)
        for error in semantic_validation_errors:
            print(f"  - {error}", file=sys.stderr)
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
