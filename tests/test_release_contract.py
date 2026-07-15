from __future__ import annotations

import importlib.util
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
CHECKER_PATH = ROOT / ".github" / "scripts" / "check_release_contract.py"
SPEC = importlib.util.spec_from_file_location("check_release_contract", CHECKER_PATH)
assert SPEC and SPEC.loader
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


SOURCE_SHA = "abcdef0123456789abcdef0123456789abcdef01"
RELEASE_TAG = "v2026.07.14-abcdef0"
ASSET_NAMES = {
    "Roger_Fleig_20260714.md",
    "Roger_Fleig_20260714.structured.md",
    "Roger_Fleig_20260714.docx",
    "Roger_Fleig_20260714.pdf",
}


def release_payload(*, draft: bool = True, names: set[str] = ASSET_NAMES) -> dict[str, object]:
    return {
        "tag_name": RELEASE_TAG,
        "target_commitish": SOURCE_SHA,
        "draft": draft,
        "assets": [
            {
                "name": name,
                "state": "uploaded",
                "size": 100,
                "digest": "sha256:" + ("a" * 64),
                "content_type": next(
                    content_type
                    for suffix, content_type in CHECKER.EXPECTED_CONTENT_TYPES.items()
                    if name.endswith(suffix)
                ),
            }
            for name in sorted(names)
        ],
    }


class ReleaseContractTests(unittest.TestCase):
    def test_local_contract_accepts_exact_four_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for name in ASSET_NAMES:
                (output / name).write_text("artifact", encoding="utf-8")

            expected = CHECKER.expected_asset_names(output, "20260714")
            CHECKER.validate_local_assets(output, expected)

            self.assertEqual(expected, ASSET_NAMES)

    def test_local_contract_rejects_extra_or_duplicate_structured_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for name in ASSET_NAMES | {"Other_20260714.structured.md"}:
                (output / name).write_text("artifact", encoding="utf-8")

            with self.assertRaisesRegex(CHECKER.ContractError, "exactly one structured"):
                CHECKER.expected_asset_names(output, "20260714")

    def test_identity_requires_tag_date_and_sha_agreement(self) -> None:
        self.assertEqual(CHECKER.validate_identity(SOURCE_SHA, RELEASE_TAG), "20260714")
        with self.assertRaisesRegex(CHECKER.ContractError, "does not match"):
            CHECKER.validate_identity(SOURCE_SHA, "v2026.07.14-1234567")

    def test_release_payload_requires_exact_uploaded_digested_assets(self) -> None:
        CHECKER.validate_release_payload(
            release_payload(),
            source_sha=SOURCE_SHA,
            release_tag=RELEASE_TAG,
            expected=ASSET_NAMES,
            expected_draft=True,
        )

        missing = release_payload(names=ASSET_NAMES - {"Roger_Fleig_20260714.pdf"})
        with self.assertRaisesRegex(CHECKER.ContractError, "exactly the four expected"):
            CHECKER.validate_release_payload(
                missing,
                source_sha=SOURCE_SHA,
                release_tag=RELEASE_TAG,
                expected=ASSET_NAMES,
                expected_draft=True,
            )

        undigested = release_payload()
        undigested["assets"][0]["digest"] = None
        with self.assertRaisesRegex(CHECKER.ContractError, "lacks a SHA-256 digest"):
            CHECKER.validate_release_payload(
                undigested,
                source_sha=SOURCE_SHA,
                release_tag=RELEASE_TAG,
                expected=ASSET_NAMES,
                expected_draft=True,
            )

    def test_workflow_drafts_verifies_then_publishes_exact_sha(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
        draft = workflow.index("draft: true")
        verify = workflow.index("Verify draft release assets")
        publish = workflow.index("Publish verified GitHub release")

        self.assertIn("target_commitish: ${{ github.sha }}", workflow)
        self.assertLess(draft, verify)
        self.assertLess(verify, publish)
        self.assertIn("-F draft=false", workflow[publish:])

    def test_changed_files_remain_outside_release_trigger_paths(self) -> None:
        changed = {
            ".github/workflows/build.yml",
            ".github/scripts/check_release_contract.py",
            "tests/test_release_contract.py",
        }
        artifact_pattern = re.compile(
            r"^(resume\.yaml|schema/.*|templates/.*|scripts/.*|pyproject\.toml|uv\.lock|Makefile|mise\.toml|\.devcontainer/(office-check\.Dockerfile|fontconfig\.conf))$"
        )
        self.assertFalse(any(artifact_pattern.fullmatch(path) for path in changed))


if __name__ == "__main__":
    unittest.main()
