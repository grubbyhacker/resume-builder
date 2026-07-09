from __future__ import annotations

import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

import yaml


DATE_ENV = "RESUME_BUILD_DATE"


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


def release_tag(date_string: str) -> str:
    return f"v{date_string[0:4]}.{date_string[4:6]}.{date_string[6:8]}"


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


def copy_named_artifact(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == destination.resolve():
        return
    shutil.copy2(source, destination)
