#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageOps

from build_metadata import default_artifact_path
from check_parse import (
    as_string_list,
    check_forbidden,
    check_order,
    check_required_exact,
    expected_resume_strings,
    load_expectations,
    load_resume,
)


PDF_RENDER_DPI = 144
INK_THRESHOLD = 16
MIN_BOTTOM_WHITESPACE_INCHES = 0.35


def require_command(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"required command not found: {name}")
    return path


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, text=True, capture_output=True)


def convert_docx_to_pdf(docx_path: Path, output_dir: Path) -> Path:
    soffice = require_command("soffice")
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"{docx_path.stem}.pdf"
    pdf_path.unlink(missing_ok=True)
    command = [
        soffice,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(docx_path),
    ]
    result = run_command(command)
    if result.returncode != 0:
        raise RuntimeError(
            "LibreOffice conversion failed:\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    if not pdf_path.exists():
        raise RuntimeError(f"LibreOffice did not create expected PDF: {pdf_path}")
    return pdf_path


def pdf_page_count(pdf_path: Path) -> int:
    pdfinfo = require_command("pdfinfo")
    result = run_command([pdfinfo, str(pdf_path)])
    if result.returncode != 0:
        raise RuntimeError(f"pdfinfo failed:\n{result.stderr}")
    match = re.search(r"^Pages:\s+(\d+)$", result.stdout, re.MULTILINE)
    if not match:
        raise RuntimeError("pdfinfo output did not include a Pages line")
    return int(match.group(1))


def extract_pdf_text(pdf_path: Path, output_dir: Path) -> str:
    pdftotext = require_command("pdftotext")
    text_path = output_dir / f"{pdf_path.stem}.txt"
    result = run_command([pdftotext, "-layout", str(pdf_path), str(text_path)])
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed:\n{result.stderr}")
    return text_path.read_text(encoding="utf-8")


def prepare_page_render_dir(pdf_path: Path, output_dir: Path) -> Path:
    for legacy_page_path in output_dir.glob("page-*.png"):
        legacy_page_path.unlink()
    page_dir = output_dir / f"{pdf_path.stem}-pages"
    if page_dir.exists():
        shutil.rmtree(page_dir)
    page_dir.mkdir(parents=True)
    return page_dir


def render_pdf_pages(pdf_path: Path, output_dir: Path) -> list[Path]:
    pdftoppm = require_command("pdftoppm")
    page_dir = prepare_page_render_dir(pdf_path, output_dir)
    page_prefix = page_dir / "page"
    result = run_command(
        [pdftoppm, "-png", "-r", str(PDF_RENDER_DPI), str(pdf_path), str(page_prefix)]
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftoppm failed:\n{result.stderr}")
    page_paths = sorted(page_dir.glob("page-*.png"), key=lambda path: int(path.stem.split("-")[-1]))
    if not page_paths:
        raise RuntimeError(f"pdftoppm created no page images in {page_dir}")
    return page_paths


def page_ink_bbox(page_path: Path) -> tuple[int, int, int, int] | None:
    with Image.open(page_path) as image:
        inverted = ImageOps.invert(image.convert("L"))
        ink_mask = inverted.point(lambda value: 255 if value >= INK_THRESHOLD else 0)
        return ink_mask.getbbox()


def check_page_image_bounds(
    page_paths: list[Path], min_bottom_whitespace_inches: float = MIN_BOTTOM_WHITESPACE_INCHES
) -> list[str]:
    errors: list[str] = []
    min_bottom_whitespace = round(min_bottom_whitespace_inches * PDF_RENDER_DPI)
    for page_number, page_path in enumerate(page_paths, start=1):
        with Image.open(page_path) as image:
            width, height = image.size
        bbox = page_ink_bbox(page_path)
        if bbox is None:
            errors.append(f"rendered PDF page {page_number} contains no visible ink")
            continue
        left, top, right, bottom = bbox
        if left == 0 or top == 0 or right == width or bottom == height:
            errors.append(f"rendered PDF page {page_number} has content touching a page edge: {bbox!r}")
        bottom_whitespace = height - bottom
        if bottom_whitespace < min_bottom_whitespace:
            errors.append(
                f"rendered PDF page {page_number} has only {bottom_whitespace}px of bottom whitespace; "
                f"minimum is {min_bottom_whitespace}px ({min_bottom_whitespace_inches:.2f}in at {PDF_RENDER_DPI} DPI)"
            )
    return errors


def normalize_text(text: str) -> str:
    text = re.sub(r"(?<=\w)-\s+(?=\w)", "", text)
    text = re.sub(r"(?<=\w)-(?=\w)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def normalized_list(values: list[str]) -> list[str]:
    return [normalize_text(value) for value in values]


def check_pdf_text(text: str, expectations: dict, resume: dict) -> list[str]:
    normalized = normalize_text(text)
    errors: list[str] = []
    errors.extend(
        check_required_exact(
            normalized,
            normalized_list(as_string_list(expectations.get("docx_required_exact"), "docx_required_exact")),
        )
    )
    errors.extend(
        check_order(
            normalized,
            normalized_list(as_string_list(expectations.get("docx_required_order"), "docx_required_order")),
        )
    )
    errors.extend(
        check_forbidden(
            normalized,
            normalized_list(as_string_list(expectations.get("docx_forbidden"), "docx_forbidden")),
        )
    )

    for label, expected in expected_resume_strings(resume):
        if normalize_text(expected) not in normalized:
            errors.append(f"YAML content missing from PDF text ({label}): {expected!r}")

    ordered_list_lines = [line for line in text.splitlines() if re.match(r"^\s*1\.\s+\S", line)]
    if ordered_list_lines:
        errors.append(f"PDF text contains lines that look like converted numbered bullets: {ordered_list_lines[:3]!r}")

    return errors


def check_office(docx_path: Path, output_dir: Path, resume_path: Path, expectations_path: Path, max_pages: int) -> int:
    resume = load_resume(resume_path)
    expectations = load_expectations(expectations_path)
    pdf_path = convert_docx_to_pdf(docx_path, output_dir)
    page_count = pdf_page_count(pdf_path)
    text = extract_pdf_text(pdf_path, output_dir)
    page_paths = render_pdf_pages(pdf_path, output_dir)

    errors: list[str] = []
    if page_count < 1:
        errors.append("rendered PDF has no pages")
    if page_count > max_pages:
        errors.append(f"rendered PDF has {page_count} pages; maximum allowed is {max_pages}")
    if len(page_paths) != page_count:
        errors.append(f"Poppler reported {page_count} PDF pages but rendered {len(page_paths)} PNG files")
    errors.extend(check_page_image_bounds(page_paths))
    errors.extend(check_pdf_text(text, expectations, resume))

    if errors:
        print(f"Office checks failed for {docx_path}:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"Office checks passed for {docx_path}; rendered PDF has {page_count} page(s)")
    print(f"Office render artifacts written to {output_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Render DOCX through LibreOffice and check PDF/text output.")
    parser.add_argument("--docx", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("output/office-render"))
    parser.add_argument("--resume", type=Path, default=Path("resume.yaml"))
    parser.add_argument("--expectations", type=Path, default=Path("tests/expected/ats_text_expectations.yaml"))
    parser.add_argument("--max-pages", type=int, default=3)
    args = parser.parse_args()

    try:
        docx_path = args.docx or default_artifact_path(args.resume, Path("output"), None, ".docx")
        return check_office(docx_path, args.output_dir, args.resume, args.expectations, args.max_pages)
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        print(f"Office check error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
