from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from date_utils import ResumeDate, format_resume_date, parse_resume_date
from validate_yaml import semantic_errors


ROOT = Path(__file__).resolve().parents[1]


class DateUtilsTest(unittest.TestCase):
    def test_canonical_dates_render_for_humans(self) -> None:
        self.assertEqual(format_resume_date("2024-12"), "Dec 2024")
        self.assertEqual(format_resume_date("present"), "Present")
        self.assertEqual(format_resume_date("1995"), "1995")

    def test_present_sorts_after_calendar_dates(self) -> None:
        self.assertGreater(parse_resume_date("present"), ResumeDate(2026, 3))

    def test_semantic_validation_rejects_unsorted_roles(self) -> None:
        resume = yaml.safe_load((ROOT / "resume.yaml").read_text(encoding="utf-8"))
        roles = resume["experience"][1]["roles"]
        roles[0], roles[1] = roles[1], roles[0]

        errors = semantic_errors(resume)

        self.assertTrue(any("reverse chronological" in error for error in errors))

    def test_semantic_validation_rejects_start_after_end(self) -> None:
        resume = yaml.safe_load((ROOT / "resume.yaml").read_text(encoding="utf-8"))
        resume["experience"][0]["roles"][0]["start"] = "2027-01"

        errors = semantic_errors(resume)

        self.assertTrue(any("later than end date" in error for error in errors))


class RoleSchemaTest(unittest.TestCase):
    def test_role_with_bullets_requires_description(self) -> None:
        schema = json.loads((ROOT / "schema/resume.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        resume = yaml.safe_load((ROOT / "resume.yaml").read_text(encoding="utf-8"))
        del resume["experience"][0]["roles"][0]["description"]

        errors = list(validator.iter_errors(resume))

        self.assertTrue(any("description" in error.message for error in errors))


if __name__ == "__main__":
    unittest.main()
