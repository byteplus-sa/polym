from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
CATALOG = SKILL_DIR / "references" / "template-slide-catalog.json"
VALIDATOR = SKILL_DIR / "scripts" / "validate_byteplus_pptx.py"
TEMPLATE = SKILL_DIR / "assets" / "BytePlus Presentation Template_FEB 2026.pptx"


class CatalogTests(unittest.TestCase):
    def test_catalog_has_all_unique_slides(self) -> None:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        slide_numbers = [slide["slide_number"] for slide in catalog["slides"]]
        self.assertEqual(slide_numbers, list(range(1, 21)))
        self.assertEqual(catalog["template"]["slide_count"], 20)

    def test_template_matches_catalog_hash_and_size(self) -> None:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        template_bytes = TEMPLATE.read_bytes()
        self.assertEqual(hashlib.sha256(template_bytes).hexdigest(), catalog["template"]["sha256"])
        self.assertEqual(len(template_bytes), catalog["template"]["size_bytes"])

    def test_catalog_slide_metadata_contract(self) -> None:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        required_fields = {
            "slide_number",
            "layout_name",
            "template_role",
            "title",
            "ocr_text",
            "visual_description",
            "regions",
            "primary_colors",
            "editable_elements",
            "usage_guidance",
            "confidence",
            "notes",
        }
        self.assertTrue(all(required_fields.issubset(slide) for slide in catalog["slides"]))


class ValidatorTests(unittest.TestCase):
    def test_template_is_valid_byteplus_pptx(self) -> None:
        result = subprocess.run(
            ["python3", str(VALIDATOR), str(TEMPLATE)],
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertEqual(report["slide_count"], 20)
        self.assertEqual(report["aspect_ratio"], "16:9")
        self.assertGreater(len(report["placeholder_warnings"]), 0)

    def test_missing_file_returns_failure_report(self) -> None:
        result = subprocess.run(
            ["python3", str(VALIDATOR), "/tmp/byteplus-ppt-missing-file.pptx"],
            check=False,
            capture_output=True,
            text=True,
        )
        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["valid"])
        self.assertGreater(len(report["errors"]), 0)

    def test_corrupt_file_returns_failure_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            corrupt_path = Path(temporary_directory) / "corrupt.pptx"
            corrupt_path.write_bytes(b"not a zip package")
            result = subprocess.run(
                ["python3", str(VALIDATOR), str(corrupt_path)],
                check=False,
                capture_output=True,
                text=True,
            )
        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["valid"])


if __name__ == "__main__":
    unittest.main()
