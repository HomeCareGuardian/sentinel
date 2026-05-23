#!/usr/bin/env python3
"""Print a short failure summary from merged JUnit for CI logs."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path

QA_ROOT = Path(__file__).resolve().parents[1]
PROFILE = os.environ.get("E2E_TARGET", "local")
REPORTS = Path(os.environ.get("E2E_REPORTS_DIR", QA_ROOT / "reports" / PROFILE))
JUNIT = REPORTS / "junit-merged.xml"


def main() -> int:
    if not JUNIT.exists():
        print(f"No {JUNIT} — skip failure summary")
        return 0

    tree = ET.parse(JUNIT)
    failures = []
    for suite in tree.getroot().iter("testsuite"):
        for case in suite.iter("testcase"):
            fail = case.find("failure")
            if fail is not None:
                name = case.get("name", "?")
                classname = case.get("classname", "")
                failures.append(f"{classname}.{name}: {(fail.get('message') or '')[:120]}")

    if not failures:
        print(f"E2E failure summary ({PROFILE}): all reported tests passed")
        return 0

    print(f"E2E failure summary ({PROFILE}):")
    for line in failures[:20]:
        print(f"  - {line}")
    if len(failures) > 20:
        print(f"  … and {len(failures) - 20} more")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
