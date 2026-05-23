#!/usr/bin/env python3
"""Merge JUnit XML files under reports/<profile>/ into junit-merged.xml."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path

QA_ROOT = Path(__file__).resolve().parents[1]
PROFILE = os.environ.get("E2E_TARGET", os.environ.get("E2E_REPORTS_DIR", "local")).split("/")[-1]
REPORTS = Path(os.environ.get("E2E_REPORTS_DIR", QA_ROOT / "reports" / PROFILE))


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    merged = ET.Element("testsuites")
    found = 0
    for path in sorted(REPORTS.glob("**/*junit*.xml")):
        if path.name == "junit-merged.xml":
            continue
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        root = tree.getroot()
        if root.tag == "testsuites":
            for child in root:
                merged.append(child)
        elif root.tag == "testsuite":
            merged.append(root)
        found += 1

    out = REPORTS / "junit-merged.xml"
    ET.ElementTree(merged).write(out, encoding="unicode", xml_declaration=True)
    print(f"Merged {found} JUnit file(s) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
