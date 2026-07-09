#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from build_metadata import build_date, load_resume, named_artifact_path


def line(value: object) -> str:
    return str(value).strip()


def write_list(lines: list[str], title: str, items: list[str]) -> None:
    lines.append(f"## {title}")
    lines.append("")
    for item in items:
        lines.append(f"- {item}")
    lines.append("")


def render_structured(resume: dict) -> str:
    profile = resume["profile"]
    lines: list[str] = [f"# Resume Source: {profile['name']}", ""]

    lines.extend(
        [
            "## Profile",
            "",
            f"- Name: {profile['name']}",
            f"- Location: {profile['location']}",
            f"- Email: {profile['email']}",
            f"- Phone: {profile['phone']}",
            f"- LinkedIn: {profile['linkedin']}",
            "- Websites:",
        ]
    )
    for website in profile.get("websites", []):
        lines.append(f"  - {website}")
    lines.append("")

    lines.extend(["## Headline", "", line(resume["headline"]), ""])
    write_list(lines, "Summary", resume["summary"])
    write_list(lines, "Skills", resume["skills"])

    projects = resume.get("projects", [])
    if projects:
        lines.extend(["## Projects", ""])
        for project in projects:
            lines.append(f"### {project['name']}")
            lines.append("")
            if project.get("url"):
                lines.append(f"- URL: {project['url']}")
            lines.append(f"- Description: {project['description']}")
            lines.append("")

    lines.extend(["## Experience", ""])
    for job in resume["experience"]:
        heading = job["company"]
        if job.get("location"):
            heading = f"{heading} - {job['location']}"
        lines.append(f"### {heading}")
        lines.append("")
        for role in job["roles"]:
            lines.append(f"#### {role['title']}")
            lines.append("")
            lines.append(f"- Start: {role['start']}")
            lines.append(f"- End: {role['end']}")
            if role.get("description"):
                lines.append(f"- Description: {role['description']}")
            bullets = role.get("bullets", [])
            if bullets:
                lines.append("- Bullets:")
                for bullet in bullets:
                    lines.append(f"  - {bullet}")
            lines.append("")

    lines.extend(["## Education", ""])
    for item in resume["education"]:
        lines.append(f"### {item['institution']}")
        lines.append("")
        lines.append(f"- Location: {item['location']}")
        lines.append(f"- Degree: {item['degree']}")
        if item.get("field"):
            lines.append(f"- Field: {item['field']}")
        if item.get("start"):
            lines.append(f"- Start: {item['start']}")
        if item.get("end"):
            lines.append(f"- End: {item['end']}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render(resume_path: Path, output_path: Path | None, date_override: str | None) -> int:
    resume = load_resume(resume_path)
    date_string = build_date(date_override)
    if output_path is None:
        output_path = named_artifact_path(Path("output"), resume, date_string, ".structured.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_structured(resume), encoding="utf-8")
    print(f"Rendered {output_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Render structure-preserving Markdown from resume YAML.")
    parser.add_argument("--resume", type=Path, default=Path("resume.yaml"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--date", default=None, help="UTC build date override in YYYYMMDD form")
    args = parser.parse_args()

    try:
        return render(args.resume, args.output, args.date)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Structured Markdown render error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
