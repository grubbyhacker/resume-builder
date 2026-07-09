#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from build_metadata import build_date, copy_named_artifact, load_resume, named_artifact_path


def require_soffice() -> str:
    path = shutil.which("soffice")
    if path is None:
        raise RuntimeError("required command not found: soffice")
    return path


def convert_docx_to_pdf(docx_path: Path, output_dir: Path) -> Path:
    soffice = require_soffice()
    output_dir.mkdir(parents=True, exist_ok=True)
    expected_pdf = output_dir / f"{docx_path.stem}.pdf"
    expected_pdf.unlink(missing_ok=True)
    result = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(docx_path)],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "LibreOffice conversion failed:\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    if not expected_pdf.exists():
        raise RuntimeError(f"LibreOffice did not create expected PDF: {expected_pdf}")
    return expected_pdf


def build_pdf(docx_path: Path, resume_path: Path, output_path: Path, date_override: str | None) -> int:
    resume = load_resume(resume_path)
    date_string = build_date(date_override)
    rendered_pdf = convert_docx_to_pdf(docx_path, output_path.parent)
    if rendered_pdf != output_path:
        output_path.unlink(missing_ok=True)
        rendered_pdf.replace(output_path)
    named_pdf = named_artifact_path(output_path.parent, resume, date_string, ".pdf")
    copy_named_artifact(output_path, named_pdf)
    print(f"Rendered {output_path}")
    print(f"Rendered {named_pdf}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Render ATS DOCX to PDF and named upload PDF.")
    parser.add_argument("--docx", type=Path, default=Path("output/ats.docx"))
    parser.add_argument("--resume", type=Path, default=Path("resume.yaml"))
    parser.add_argument("--output", type=Path, default=Path("output/ats.pdf"))
    parser.add_argument("--date", default=None, help="UTC build date override in YYYYMMDD form")
    args = parser.parse_args()

    try:
        return build_pdf(args.docx, args.resume, args.output, args.date)
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        print(f"PDF build error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
