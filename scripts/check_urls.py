#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

import yaml

from build_metadata import load_resume


BLOCKED_BUT_EXISTS_STATUSES = {401, 403, 405, 429, 999}
USER_AGENT = "resume-builder-url-check/1.0"


def collect_urls(resume: dict) -> list[tuple[str, str]]:
    urls: list[tuple[str, str]] = []
    profile = resume.get("profile", {})
    if isinstance(profile, dict):
        linkedin = profile.get("linkedin")
        if isinstance(linkedin, str):
            urls.append(("profile.linkedin", linkedin))
        websites = profile.get("websites", [])
        if isinstance(websites, list):
            for index, website in enumerate(websites):
                if isinstance(website, str):
                    urls.append((f"profile.websites[{index}]", website))

    projects = resume.get("projects", [])
    if isinstance(projects, list):
        for index, project in enumerate(projects):
            if isinstance(project, dict) and isinstance(project.get("url"), str):
                urls.append((f"projects[{index}].url", project["url"]))

    return urls


def open_url(url: str, method: str, timeout: int) -> int:
    request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def check_url(url: str, timeout: int, retries: int) -> tuple[bool, str]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            status = open_url(url, "HEAD", timeout)
            if status == 405:
                status = open_url(url, "GET", timeout)
            if 200 <= status < 400:
                return True, f"HTTP {status}"
            if status in BLOCKED_BUT_EXISTS_STATUSES:
                return True, f"HTTP {status} (reachable but blocked/limited)"
            return False, f"HTTP {status}"
        except (OSError, urllib.error.URLError, ssl.SSLError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1)
    return False, str(last_error)


def check_urls(urls: Iterable[tuple[str, str]], timeout: int, retries: int) -> int:
    errors: list[str] = []
    checked = 0
    for label, url in urls:
        checked += 1
        ok, detail = check_url(url, timeout, retries)
        if ok:
            print(f"URL ok: {label}: {url} ({detail})")
        else:
            errors.append(f"{label}: {url} ({detail})")

    if errors:
        print("URL checks failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"URL checks passed for {checked} URL(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check resume URLs for basic reachability.")
    parser.add_argument("--resume", type=Path, default=Path("resume.yaml"))
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--retries", type=int, default=1)
    args = parser.parse_args()

    try:
        resume = load_resume(args.resume)
        return check_urls(collect_urls(resume), args.timeout, args.retries)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"URL check error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
