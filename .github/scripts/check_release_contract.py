#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
TAG_PATTERN = re.compile(r"^v(?P<year>\d{4})\.(?P<month>\d{2})\.(?P<day>\d{2})-(?P<sha>[0-9a-f]{7})$")
EXPECTED_CONTENT_TYPES = {
    ".structured.md": "text/markdown",
    ".md": "text/markdown",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
}


class ContractError(ValueError):
    pass


def expected_asset_names(output_dir: Path, build_date: str) -> set[str]:
    matches = sorted(path for path in output_dir.glob(f"*_{build_date}*") if path.is_file())
    structured = [path for path in matches if path.name.endswith(".structured.md")]
    if len(structured) != 1:
        raise ContractError(
            f"expected exactly one structured Markdown asset for {build_date}, found {len(structured)}"
        )

    structured_name = structured[0].name
    stem = structured_name.removesuffix(".structured.md")
    return {
        f"{stem}.md",
        structured_name,
        f"{stem}.docx",
        f"{stem}.pdf",
    }


def validate_identity(source_sha: str, release_tag: str) -> str:
    source_sha = source_sha.lower()
    if SHA_PATTERN.fullmatch(source_sha) is None:
        raise ContractError("source SHA must be exactly 40 hexadecimal characters")
    match = TAG_PATTERN.fullmatch(release_tag)
    if match is None:
        raise ContractError("release tag must match vYYYY.MM.DD-sha7")
    if match.group("sha") != source_sha[:7]:
        raise ContractError("release tag SHA does not match the source commit")
    return "".join((match.group("year"), match.group("month"), match.group("day")))


def validate_local_assets(output_dir: Path, expected: set[str]) -> None:
    actual = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise ContractError(
            f"release output mismatch; missing={missing or 'none'}, unexpected={unexpected or 'none'}"
        )


def validate_release_payload(
    payload: object,
    *,
    source_sha: str,
    release_tag: str,
    expected: set[str],
    expected_draft: bool,
) -> None:
    if not isinstance(payload, dict):
        raise ContractError("release API response must be a JSON object")
    if payload.get("tag_name") != release_tag:
        raise ContractError("release API tag does not match generated metadata")
    if payload.get("target_commitish") != source_sha:
        raise ContractError("release target_commitish is not the exact source commit")
    if payload.get("draft") is not expected_draft:
        raise ContractError(f"release draft state is not {expected_draft}")

    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise ContractError("release API response has no asset list")
    names = [asset.get("name") for asset in assets if isinstance(asset, dict)]
    if len(assets) != 4 or len(names) != 4 or set(names) != expected:
        raise ContractError(f"release must contain exactly the four expected assets; found={names}")
    if len([name for name in names if name.endswith(".structured.md")]) != 1:
        raise ContractError("release must contain exactly one structured Markdown asset")

    for asset in assets:
        if not isinstance(asset, dict):
            raise ContractError("release asset metadata must be a JSON object")
        name = asset.get("name")
        expected_content_type = next(
            (content_type for suffix, content_type in EXPECTED_CONTENT_TYPES.items() if name.endswith(suffix)),
            None,
        )
        if asset.get("content_type") != expected_content_type:
            raise ContractError(f"release asset {name!r} has an invalid content type")
        if asset.get("state") != "uploaded":
            raise ContractError(f"release asset {name!r} is not uploaded")
        if not isinstance(asset.get("size"), int) or asset["size"] <= 0:
            raise ContractError(f"release asset {name!r} has an invalid size")
        if not isinstance(asset.get("digest"), str) or DIGEST_PATTERN.fullmatch(asset["digest"]) is None:
            raise ContractError(f"release asset {name!r} lacks a SHA-256 digest")


def parse_bool(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the deterministic resume release contract.")
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--release-json", type=Path)
    parser.add_argument("--expected-draft", type=parse_bool)
    args = parser.parse_args()

    try:
        build_date = validate_identity(args.source_sha, args.release_tag)
        env_date = os.environ.get("RESUME_BUILD_DATE")
        env_sha = os.environ.get("RESUME_BUILD_SHA")
        if env_date != build_date:
            raise ContractError("release tag date does not match RESUME_BUILD_DATE")
        if env_sha is None or env_sha.lower() != args.source_sha.lower()[:7]:
            raise ContractError("source commit does not match RESUME_BUILD_SHA")

        expected = expected_asset_names(args.output_dir, build_date)
        validate_local_assets(args.output_dir, expected)
        if args.release_json is not None:
            if args.expected_draft is None:
                raise ContractError("--release-json requires --expected-draft")
            payload = json.loads(args.release_json.read_text(encoding="utf-8"))
            validate_release_payload(
                payload,
                source_sha=args.source_sha.lower(),
                release_tag=args.release_tag,
                expected=expected,
                expected_draft=args.expected_draft,
            )
    except (ContractError, json.JSONDecodeError, OSError) as exc:
        print(f"Release contract check failed: {exc}", file=sys.stderr)
        return 1

    print("Release contract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
