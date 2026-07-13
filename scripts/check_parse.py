#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from build_metadata import default_artifact_path
from date_utils import format_resume_date


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
TABLE_RE = re.compile(r"^\s*\|.+\|\s*$", re.MULTILINE)
IMAGE_RE = re.compile(r"!\[[^\]]*]\([^)]*\)")
HTML_BLOCK_RE = re.compile(r"^\s*</?[A-Za-z][^>]*>\s*$", re.MULTILINE)
ROLE_NOUN_START_RE = re.compile(r"^(?:[-•]\s*)?(Author|Executive|Lead|Manager|Director)\b")


def load_expectations(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the document root")
    return data


def load_resume(path: Path) -> dict:
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


def append_string(value: object, label: str, strings: list[tuple[str, str]]) -> None:
    if isinstance(value, str) and value:
        strings.append((label, value))


def expected_resume_strings(resume: dict, *, display_dates: bool = True) -> list[tuple[str, str]]:
    strings: list[tuple[str, str]] = []
    profile = resume.get("profile", {})
    if isinstance(profile, dict):
        for key in ("name", "location", "email", "phone", "linkedin"):
            append_string(profile.get(key), f"profile.{key}", strings)
        websites = profile.get("websites", [])
        if isinstance(websites, list):
            for index, website in enumerate(websites):
                append_string(website, f"profile.websites[{index}]", strings)

    append_string(resume.get("headline"), "headline", strings)

    for section_name in ("summary", "skills"):
        items = resume.get(section_name, [])
        if isinstance(items, list):
            for index, item in enumerate(items):
                append_string(item, f"{section_name}[{index}]", strings)

    projects = resume.get("projects", [])
    if isinstance(projects, list):
        for project_index, project in enumerate(projects):
            if not isinstance(project, dict):
                continue
            for key in ("name", "url", "description"):
                append_string(project.get(key), f"projects[{project_index}].{key}", strings)

    experience = resume.get("experience", [])
    if isinstance(experience, list):
        for job_index, job in enumerate(experience):
            if not isinstance(job, dict):
                continue
            append_string(job.get("company"), f"experience[{job_index}].company", strings)
            append_string(job.get("location"), f"experience[{job_index}].location", strings)
            roles = job.get("roles", [])
            if not isinstance(roles, list):
                continue
            for role_index, role in enumerate(roles):
                if not isinstance(role, dict):
                    continue
                append_string(role.get("title"), f"experience[{job_index}].roles[{role_index}].title", strings)
                for key in ("start", "end"):
                    value = role.get(key)
                    if display_dates and isinstance(value, str):
                        value = format_resume_date(value)
                    append_string(value, f"experience[{job_index}].roles[{role_index}].{key}", strings)
                append_string(
                    role.get("description"),
                    f"experience[{job_index}].roles[{role_index}].description",
                    strings,
                )
                bullets = role.get("bullets", [])
                if isinstance(bullets, list):
                    for bullet_index, bullet in enumerate(bullets):
                        append_string(
                            bullet,
                            f"experience[{job_index}].roles[{role_index}].bullets[{bullet_index}]",
                            strings,
                        )

    education = resume.get("education", [])
    if isinstance(education, list):
        for education_index, item in enumerate(education):
            if not isinstance(item, dict):
                continue
            for key in ("institution", "location", "degree", "field", "start", "end"):
                value = item.get(key)
                if display_dates and key in {"start", "end"} and isinstance(value, str):
                    value = format_resume_date(value)
                append_string(value, f"education[{education_index}].{key}", strings)

    return strings


def role_heading(company: str, location: str, role: dict) -> str:
    start = format_resume_date(role["start"])
    end = format_resume_date(role["end"])
    return f"{role['title']}, {company} | {location} | {start} - {end}"


def check_markdown_role_headings(text: str, resume: dict) -> list[str]:
    errors: list[str] = []
    lines = [line.strip() for line in text.splitlines()]
    cursor = 0

    for job_index, job in enumerate(resume.get("experience", [])):
        if not isinstance(job, dict):
            continue
        company = job.get("company", "<unknown company>")
        location = job.get("location", "<unknown location>")
        legacy_heading = f"### {company} - {location}"
        if legacy_heading in lines:
            errors.append(
                f"experience[{job_index}] uses a shared employer heading; every role must repeat employer metadata"
            )

        for role_index, role in enumerate(job.get("roles", [])):
            if not isinstance(role, dict):
                continue
            try:
                expected = f"### {role_heading(str(company), str(location), role)}"
            except KeyError as exc:
                errors.append(
                    f"experience[{job_index}].roles[{role_index}] is missing key needed for Markdown heading: {exc}"
                )
                continue
            try:
                found = lines.index(expected, cursor)
            except ValueError:
                errors.append(
                    f"complete Markdown role heading missing for experience[{job_index}].roles[{role_index}]: "
                    f"{expected!r}"
                )
                continue
            cursor = found + 1

    return errors


def check_yaml_content_present(text: str, resume: dict, *, display_dates: bool = True) -> list[str]:
    errors: list[str] = []
    for label, expected in expected_resume_strings(resume, display_dates=display_dates):
        if expected not in text:
            errors.append(f"YAML content missing from output ({label}): {expected!r}")
    return errors


def expected_document_order(resume: dict, *, markdown: bool) -> list[str]:
    prefix = "## " if markdown else ""
    order = [resume["profile"]["name"], resume["headline"], f"{prefix}Summary", f"{prefix}Skills"]
    if resume.get("projects"):
        order.append(f"{prefix}Projects")
    order.extend((f"{prefix}Professional Experience", f"{prefix}Education"))
    return order


def check_role_boundaries(text: str, resume: dict) -> list[str]:
    errors: list[str] = []
    roles: list[tuple[str, str, dict]] = []

    experience = resume.get("experience", [])
    if not isinstance(experience, list):
        return errors

    for job in experience:
        if not isinstance(job, dict):
            continue
        company = job.get("company", "<unknown company>")
        location = job.get("location", "<unknown location>")
        job_roles = job.get("roles", [])
        if not isinstance(job_roles, list):
            continue
        for role in job_roles:
            if isinstance(role, dict):
                roles.append((str(company), str(location), role))

    role_offsets: list[tuple[str, dict, int]] = []
    cursor = 0
    for company, location, role in roles:
        company_location = f"{company} / {location}"
        try:
            heading = role_heading(company, location, role)
        except KeyError as exc:
            errors.append(f"role under {company_location} is missing key needed for heading: {exc}")
            continue
        found = text.find(heading, cursor)
        if found == -1:
            errors.append(f"role heading not found in expected order under {company_location}: {heading!r}")
            continue
        role_offsets.append((company_location, role, found))
        cursor = found + len(heading)

    for index, (company, role, start) in enumerate(role_offsets):
        end = role_offsets[index + 1][2] if index + 1 < len(role_offsets) else len(text)
        role_text = text[start:end]
        bullets = role.get("bullets", [])
        description = role.get("description")
        cursor = -1
        if isinstance(description, str):
            description_offset = role_text.find(description)
            if description_offset == -1:
                errors.append(f"description missing from role block ({company} / {role.get('title')}): {description!r}")
            else:
                cursor = description_offset
        if not isinstance(bullets, list):
            continue
        for bullet in bullets:
            if not isinstance(bullet, str):
                continue
            found = role_text.find(bullet, cursor + 1)
            if found == -1:
                errors.append(f"bullet missing from role block ({company} / {role.get('title')}): {bullet!r}")
                continue
            cursor = found

    return errors


def check_role_noun_starts(text: str) -> list[str]:
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if ROLE_NOUN_START_RE.search(stripped):
            errors.append(f"line starts with title-like noun at line {line_number}: {stripped!r}")
    return errors


def check_education_degree_fields(text: str, resume: dict) -> list[str]:
    errors: list[str] = []
    education = resume.get("education", [])
    if not isinstance(education, list):
        return errors

    for index, item in enumerate(education):
        if not isinstance(item, dict):
            continue
        degree = item.get("degree")
        field = item.get("field")
        institution = item.get("institution")
        if not isinstance(degree, str) or not isinstance(field, str):
            errors.append(f"education[{index}] must keep degree and field as separate YAML strings")
            continue
        if re.search(r"\b(BS|BA|MS|MA|PhD)\b", degree):
            errors.append(f"education[{index}].degree should be spelled out, not abbreviated: {degree!r}")
        rendered_line = f"{degree} in {field}"
        if rendered_line not in text:
            errors.append(f"education[{index}] degree/field line missing: {rendered_line!r}")
        if isinstance(institution, str) and institution in text:
            if text.find(institution) > text.find(rendered_line):
                errors.append(f"education[{index}] institution should appear before degree/field")

    return errors


def check_ats_text(text: str, expectations: dict, resume: dict) -> list[str]:
    errors: list[str] = []
    errors.extend(check_required_exact(text, as_string_list(expectations.get("required_exact"), "required_exact")))
    errors.extend(check_order(text, as_string_list(expectations.get("required_order"), "required_order")))
    errors.extend(check_order(text, expected_document_order(resume, markdown=True)))
    errors.extend(check_forbidden(text, as_string_list(expectations.get("forbidden"), "forbidden")))
    errors.extend(check_yaml_content_present(text, resume))
    errors.extend(check_markdown_role_headings(text, resume))
    errors.extend(check_role_boundaries(text, resume))
    errors.extend(check_role_noun_starts(text))
    errors.extend(check_education_degree_fields(text, resume))

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
    parser.add_argument("--resume", type=Path, default=Path("resume.yaml"))
    parser.add_argument("--markdown", type=Path, default=None)
    parser.add_argument("--expectations", type=Path, default=Path("tests/expected/ats_text_expectations.yaml"))
    args = parser.parse_args()

    try:
        markdown_path = args.markdown or default_artifact_path(args.resume, Path("output"), None, ".md")
        text = markdown_path.read_text(encoding="utf-8")
        resume = load_resume(args.resume)
        expectations = load_expectations(args.expectations)
        errors = check_ats_text(text, expectations, resume)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Parse check error: {exc}", file=sys.stderr)
        return 1

    if errors:
        print(f"Parser checks failed for {markdown_path}:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"Parser checks passed for {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
