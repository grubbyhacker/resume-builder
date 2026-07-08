#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError, select_autoescape


def load_resume(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the document root")
    return data


def render(resume_path: Path, template_path: Path, output_path: Path) -> int:
    resume = load_resume(resume_path)
    environment = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=select_autoescape(disabled_extensions=("j2", "md")),
    )
    template = environment.get_template(template_path.name)
    rendered = template.render(**resume).rstrip() + "\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"Rendered {output_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Render ATS-safe Markdown from resume YAML.")
    parser.add_argument("--resume", type=Path, default=Path("resume.yaml"))
    parser.add_argument("--template", type=Path, default=Path("templates/ats.md.j2"))
    parser.add_argument("--output", type=Path, default=Path("output/ats.md"))
    args = parser.parse_args()

    try:
        return render(args.resume, args.template, args.output)
    except (OSError, ValueError, yaml.YAMLError, TemplateError) as exc:
        print(f"Render error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
