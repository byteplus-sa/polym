from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Optional, Tuple
from xml.etree import ElementTree


EXPECTED_CX = 12192000
EXPECTED_CY = 6858000
REQUIRED_PARTS = {
    "[Content_Types].xml",
    "ppt/presentation.xml",
    "ppt/_rels/presentation.xml.rels",
}
PLACEHOLDER_PATTERNS = (
    re.compile(r"click to edit", re.IGNORECASE),
    re.compile(r"insert date", re.IGNORECASE),
    re.compile(r"insert logo", re.IGNORECASE),
    re.compile(r"generic image\s*\(replaceable\)", re.IGNORECASE),
    re.compile(r"pellentesque|maecenas|vivamus", re.IGNORECASE),
    re.compile(r"\btitle text\b", re.IGNORECASE),
    re.compile(r"^\s*(header|subheader|title|content|description|annotation|xx%)\s*$", re.IGNORECASE),
    re.compile(r"^\s*#\d+\s+point\s*$", re.IGNORECASE),
    re.compile(r"case study\s*\(which byteplus product\)", re.IGNORECASE),
)
DRAWING_NAMESPACE = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
PRESENTATION_NAMESPACE = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    return parser.parse_args()


def slide_sort_key(name: str) -> int:
    match = re.search(r"slide(\d+)\.xml$", name)
    return int(match.group(1)) if match else 0


def extract_text(xml_bytes: bytes) -> list[str]:
    root = ElementTree.fromstring(xml_bytes)
    return [node.text or "" for node in root.iter(f"{DRAWING_NAMESPACE}t") if node.text]


def presentation_size(xml_bytes: bytes) -> Tuple[Optional[int], Optional[int]]:
    root = ElementTree.fromstring(xml_bytes)
    size = root.find(f"{PRESENTATION_NAMESPACE}sldSz")
    if size is None:
        return None, None
    return int(size.attrib.get("cx", "0")), int(size.attrib.get("cy", "0"))


def collect_fonts(archive: zipfile.ZipFile, names: list[str]) -> list[str]:
    fonts: set[str] = set()
    pattern = re.compile(r'typeface="([^"]+)"')
    for name in names:
        if not re.match(r"ppt/(slides|slideMasters|slideLayouts|theme)/.*\.xml$", name):
            continue
        xml = archive.read(name).decode("utf-8", errors="replace")
        fonts.update(pattern.findall(xml))
    return sorted(fonts)


def validate(path: Path) -> Tuple[dict[str, object], bool]:
    errors: list[str] = []
    warnings: list[dict[str, object]] = []
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                errors.append(f"Corrupt ZIP member: {bad_member}")
            names = archive.namelist()
            missing_parts = sorted(REQUIRED_PARTS.difference(names))
            if missing_parts:
                errors.append(f"Missing required package parts: {', '.join(missing_parts)}")
            if "ppt/presentation.xml" in names:
                cx, cy = presentation_size(archive.read("ppt/presentation.xml"))
            else:
                cx, cy = None, None
            if (cx, cy) != (EXPECTED_CX, EXPECTED_CY):
                errors.append(f"Unexpected slide size: {cx},{cy}; expected {EXPECTED_CX},{EXPECTED_CY}")
            slide_names = sorted(
                (name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
                key=slide_sort_key,
            )
            for slide_number, name in enumerate(slide_names, start=1):
                texts = extract_text(archive.read(name))
                matches = sorted({text for text in texts if any(pattern.search(text) for pattern in PLACEHOLDER_PATTERNS)})
                if matches:
                    warnings.append({"slide_number": slide_number, "placeholder_text": matches})
            report = {
                "schema_version": "1.0",
                "pptx": str(path),
                "valid": not errors,
                "slide_count": len(slide_names),
                "slide_size_emu": {"cx": cx, "cy": cy},
                "aspect_ratio": "16:9" if (cx, cy) == (EXPECTED_CX, EXPECTED_CY) else "unexpected",
                "fonts": collect_fonts(archive, names),
                "placeholder_warnings": warnings,
                "errors": errors,
            }
    except (FileNotFoundError, zipfile.BadZipFile, ElementTree.ParseError, OSError) as error:
        report = {
            "schema_version": "1.0",
            "pptx": str(path),
            "valid": False,
            "slide_count": 0,
            "slide_size_emu": {"cx": None, "cy": None},
            "aspect_ratio": "unknown",
            "fonts": [],
            "placeholder_warnings": [],
            "errors": [str(error)],
        }
    return report, bool(report["valid"])


def main() -> int:
    args = parse_args()
    path = args.pptx.expanduser().resolve()
    report, valid = validate(path)
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.json_path:
        json_path = args.json_path.expanduser().resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
