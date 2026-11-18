"""Параметр платформы DisableUnsafeActionProtection в conf.cfg.

1С отключает защиту от опасных действий для баз, строка соединения которых
целиком подходит под одно из регулярных выражений параметра (через «;»).
Проверено на 8.5.1.1343: ``.*ib`` для ``File="/x/ib";`` не срабатывает (сравнение
со всей строкой), ``.*ib\\W.*`` срабатывает и не задевает ``/x/ib2``. Кавычки
в выражении 1С разбирает по-своему (``.*File="…";.*`` срабатывает для любой
базы), поэтому в предлагаемой строке их нет. Файл правит
администратор компьютера; onec-ops его только читает.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

PARAMETER = "DisableUnsafeActionProtection"


def conf_files(platform_path: Path) -> list[Path]:
    """Возвращает conf.cfg платформы: каталог версии и общий каталог 1cv8.

    Linux: /opt/1cv8/x86_64/<версия>/conf и /opt/1cv8/conf.
    Windows: C:\\Program Files\\1cv8\\<версия>\\bin\\conf и C:\\Program Files\\1cv8\\conf.
    """
    platform_dir = Path(platform_path).parent
    candidates = [platform_dir / "conf" / "conf.cfg"]
    if len(platform_dir.parents) >= 2:
        candidates.append(platform_dir.parents[1] / "conf" / "conf.cfg")
    unique: list[Path] = []
    for path in candidates:
        if path not in unique:
            unique.append(path)
    return unique


def read_patterns(files: list[Path]) -> list[tuple[Path, str]]:
    """Читает регулярные выражения параметра из найденных conf.cfg."""
    patterns: list[tuple[Path, str]] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip().lower() == PARAMETER.lower():
                patterns += [(path, item.strip()) for item in value.split(";") if item.strip()]
    return patterns


def connection_string(ib: Path) -> str:
    """Строка соединения файловой ИБ в том виде, в каком её сравнивает 1С."""
    return f'File="{ib}";'


def disabled_by(ib: Path, platform_path: Path) -> Path | None:
    """Возвращает conf.cfg, где защита для базы уже отключена, иначе None.

    Регулярные выражения 1С близки к Python, но не совпадают полностью:
    результат — подсказка, а не гарантия.
    """
    target = connection_string(ib)
    for path, pattern in read_patterns(conf_files(platform_path)):
        try:
            if re.fullmatch(pattern, target, re.IGNORECASE):
                return path
        except re.error:
            logger.debug("Не разобрано выражение %s в %s", pattern, path)
    return None


def suggested_line(ib: Path) -> str:
    """Строка conf.cfg, которая отключает защиту только для этой базы."""
    escaped = re.sub(r"([\\.^$|?*+()\[\]{}])", r"\\\1", str(ib))
    return f"{PARAMETER}=.*{escaped}\\W.*"
