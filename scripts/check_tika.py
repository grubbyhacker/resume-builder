#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

from build_metadata import default_artifact_path
from check_parse import check_role_boundaries, expected_resume_strings, load_resume


def request(method: str, url: str, data: bytes | None = None, content_type: str | None = None) -> tuple[int, bytes]:
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.status, response.read()


def wait_for_tika(server_url: str, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            status, _ = request("GET", f"{server_url.rstrip('/')}/tika")
            if status == 200:
                return
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"Tika server did not become ready at {server_url}: {last_error}")


def extract_text(server_url: str, docx_path: Path) -> str:
    data = docx_path.read_bytes()
    status, body = request(
        "PUT",
        f"{server_url.rstrip('/')}/tika",
        data=data,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    if status != 200:
        raise RuntimeError(f"Tika returned HTTP {status}")
    text = body.decode("utf-8", errors="replace")
    if not text.strip():
        raise RuntimeError("Tika returned no text content")
    return text


def normalize_extracted_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+:", ":", text)
    return re.sub(r"\s+", " ", text).strip()


def check_yaml_content_present_normalized(text: str, resume: dict) -> list[str]:
    normalized_text = normalize_extracted_text(text)
    errors: list[str] = []
    for label, expected in expected_resume_strings(resume):
        if normalize_extracted_text(expected) not in normalized_text:
            errors.append(f"YAML content missing from output ({label}): {expected!r}")
    return errors


def check_tika(docx_path: Path, resume_path: Path, server_url: str, timeout_seconds: int) -> int:
    wait_for_tika(server_url, timeout_seconds)
    resume = load_resume(resume_path)
    text = extract_text(server_url, docx_path)
    normalized_text = normalize_extracted_text(text)
    errors = []
    errors.extend(check_yaml_content_present_normalized(normalized_text, resume))
    errors.extend(check_role_boundaries(normalized_text, resume))

    if errors:
        print(f"Tika checks failed for {docx_path}:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"Tika checks passed for {docx_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DOCX extraction through a running Apache Tika server.")
    parser.add_argument("--resume", type=Path, default=Path("resume.yaml"))
    parser.add_argument("--docx", type=Path, default=None)
    parser.add_argument("--server-url", default="http://127.0.0.1:9998")
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()

    try:
        docx_path = args.docx or default_artifact_path(args.resume, Path("output"), None, ".docx")
        return check_tika(docx_path, args.resume, args.server_url, args.timeout)
    except (OSError, RuntimeError, ValueError, yaml.YAMLError, urllib.error.URLError) as exc:
        print(f"Tika check error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
