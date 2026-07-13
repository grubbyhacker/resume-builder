from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import yaml

from check_parse import check_markdown_role_headings, role_heading
from render_markdown import render


ROOT = Path(__file__).resolve().parents[1]


class MarkdownRoleHeadingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.resume_path = ROOT / "resume.yaml"
        self.resume = yaml.safe_load(self.resume_path.read_text(encoding="utf-8"))
        self.template_path = ROOT / "templates/ats.md.j2"

    def render_markdown(self) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "resume.md"
            with redirect_stdout(StringIO()):
                render(self.resume_path, self.template_path, output_path, "20260713")
            return output_path.read_text(encoding="utf-8")

    def test_every_role_has_a_complete_heading(self) -> None:
        text = self.render_markdown()

        self.assertEqual(check_markdown_role_headings(text, self.resume), [])
        for job in self.resume["experience"]:
            for role in job["roles"]:
                expected = f"### {role_heading(job['company'], job['location'], role)}"
                self.assertIn(expected, text.splitlines())

    def test_shared_employer_heading_is_rejected(self) -> None:
        text = self.render_markdown()
        job = self.resume["experience"][1]
        text = text.replace(
            f"### {role_heading(job['company'], job['location'], job['roles'][0])}",
            f"### {job['company']} - {job['location']}",
            1,
        )

        errors = check_markdown_role_headings(text, self.resume)

        self.assertTrue(any("shared employer heading" in error for error in errors))
        self.assertTrue(any("complete Markdown role heading missing" in error for error in errors))

    def test_incomplete_role_heading_is_rejected(self) -> None:
        text = self.render_markdown()
        job = self.resume["experience"][1]
        role = job["roles"][1]
        complete = f"### {role_heading(job['company'], job['location'], role)}"
        incomplete_headings = {
            "title": f"### {job['company']} | {job['location']} | Apr 2011 - Aug 2018",
            "company": f"### {role['title']} | {job['location']} | Apr 2011 - Aug 2018",
            "location": f"### {role['title']}, {job['company']} | Apr 2011 - Aug 2018",
            "dates": f"### {role['title']}, {job['company']} | {job['location']}",
        }

        for missing_field, incomplete in incomplete_headings.items():
            with self.subTest(missing_field=missing_field):
                errors = check_markdown_role_headings(text.replace(complete, incomplete, 1), self.resume)
                self.assertTrue(any("complete Markdown role heading missing" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
