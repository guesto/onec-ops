"""Выводит упавшие тесты из JUnit-отчёта одной аннотацией GitHub Actions."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_DETAIL = 400
MAX_TOTAL = 60000


def main() -> int:
    report = Path(sys.argv[1])
    if not report.is_file():
        return 0
    lines = []
    for case in ET.parse(report).getroot().iter("testcase"):
        for problem in (*case.findall("failure"), *case.findall("error")):
            detail = (problem.get("message") or "").replace("\r", " ").replace("\n", " ")
            lines.append(f"{case.get('classname')}::{case.get('name')}: {detail[:MAX_DETAIL]}")
    if not lines:
        return 0
    message = f"Упало тестов: {len(lines)}\n" + "\n".join(lines)
    encoded = message[:MAX_TOTAL].replace("%", "%25").replace("\n", "%0A")
    sys.stdout.buffer.write(f"::error title=pytest::{encoded}\n".encode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
