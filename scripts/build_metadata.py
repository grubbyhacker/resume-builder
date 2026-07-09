from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path

import yaml


DATE_ENV = "RESUME_BUILD_DATE"
SHA_ENV = "RESUME_BUILD_SHA"


def load_resume(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the document root")
    return data


def build_date(value: str | None = None) -> str:
    raw = value or os.environ.get(DATE_ENV)
    if raw is None:
        return datetime.now(UTC).strftime("%Y%m%d")
    if not re.fullmatch(r"\d{8}", raw):
        raise ValueError(f"build date must be YYYYMMDD, got {raw!r}")
    return raw


def build_sha(value: str | None = None) -> str | None:
    raw = value or os.environ.get(SHA_ENV)
    if raw is None or raw == "":
        return None
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", raw):
        raise ValueError(f"build SHA must be 7-40 hex characters, got {raw!r}")
    return raw[:7].lower()


def build_identifier(date_string: str, sha: str | None) -> str:
    if sha is None:
        return date_string
    return f"{date_string}-{sha}"


def release_tag(date_string: str, sha: str | None = None) -> str:
    base = f"v{date_string[0:4]}.{date_string[4:6]}.{date_string[6:8]}"
    if sha is None:
        return base
    return f"{base}-{sha}"


def profile_slug(name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", name).strip()
    if not normalized:
        raise ValueError("profile.name did not produce a usable filename slug")
    return "_".join(normalized.split())


def named_artifact_path(output_dir: Path, resume: dict, date_string: str, suffix: str) -> Path:
    profile = resume.get("profile")
    if not isinstance(profile, dict) or not isinstance(profile.get("name"), str):
        raise ValueError("resume profile.name is required for named artifact output")
    return output_dir / f"{profile_slug(profile['name'])}_{date_string}{suffix}"


def default_artifact_path(resume_path: Path, output_dir: Path, date_override: str | None, suffix: str) -> Path:
    resume = load_resume(resume_path)
    return named_artifact_path(output_dir, resume, build_date(date_override), suffix)
