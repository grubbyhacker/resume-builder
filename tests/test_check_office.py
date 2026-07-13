from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from check_office import check_page_image_bounds, page_ink_bbox, prepare_page_render_dir, sparse_trailing_page_warnings


class PageImageChecksTest(unittest.TestCase):
    def test_inverted_threshold_finds_ink_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            page_path = Path(temporary_directory) / "page.png"
            image = Image.new("RGB", (100, 120), "white")
            ImageDraw.Draw(image).rectangle((10, 20, 79, 89), fill="black")
            image.save(page_path)

            self.assertEqual(page_ink_bbox(page_path), (10, 20, 80, 90))

    def test_bottom_safety_zone_rejects_low_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            page_path = Path(temporary_directory) / "page.png"
            image = Image.new("RGB", (100, 144), "white")
            ImageDraw.Draw(image).rectangle((10, 20, 79, 134), fill="black")
            image.save(page_path)

            errors = check_page_image_bounds([page_path], min_bottom_whitespace_inches=0.10)

            self.assertEqual(len(errors), 1)
            self.assertIn("bottom whitespace", errors[0])

    def test_page_render_directory_removes_stale_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            pdf_path = output_dir / "tailored-resume.pdf"
            page_dir = output_dir / "tailored-resume-pages"
            page_dir.mkdir()
            (page_dir / "page-3.png").touch()
            legacy_page_path = output_dir / "page-3.png"
            legacy_page_path.touch()

            prepared = prepare_page_render_dir(pdf_path, output_dir)

            self.assertEqual(prepared, page_dir)
            self.assertEqual(list(prepared.iterdir()), [])
            self.assertFalse(legacy_page_path.exists())

    def test_sparse_trailing_page_is_advisory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            page_paths = []
            for page_number in (1, 2):
                page_path = Path(temporary_directory) / f"page-{page_number}.png"
                image = Image.new("RGB", (144, 144), "white")
                bottom = 120 if page_number == 1 else 50
                ImageDraw.Draw(image).rectangle((10, 10, 120, bottom), fill="black")
                image.save(page_path)
                page_paths.append(page_path)

            warnings = sparse_trailing_page_warnings(page_paths, minimum_ink_height_inches=0.50)

            self.assertEqual(len(warnings), 1)
            self.assertIn("sparse trailing page", warnings[0])


if __name__ == "__main__":
    unittest.main()
