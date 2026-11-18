"""Чтение ошибок из журнала регистрации файловой ИБ (формат .lgp)."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Запись журнала: {ГГГГММДДччммсс,статус,\n{транзакция},пользователь,компьютер,
# приложение,соединение,событие,важность,"комментарий",...
# Важность E — ошибка. Кавычки внутри комментария удваиваются.
_ERROR_RECORD = re.compile(
    r'\{(\d{14}),\w,\s*\{[^{}]*\},(?:\d+,){5}E,"((?:[^"]|"")*)"',
)
_MAX_ERRORS = 5


def read_errors(ib: Path, since: datetime) -> list[str]:
    """Возвращает тексты ошибок журнала ИБ, записанных не раньше ``since``.

    1С пишет в журнал местное время, поэтому ``since`` сравнивается в местном поясе.
    Журнал в формате SQLite (.lgd) не читается. Сбой чтения не ошибка:
    журнал нужен только для подсказки.
    """
    log_dir = Path(ib) / "1Cv8Log"
    stamp = since.astimezone().strftime("%Y%m%d%H%M%S")
    errors: list[str] = []
    try:
        files = sorted(log_dir.glob("*.lgp"))
    except OSError:
        return []
    for path in files:
        try:
            if path.stat().st_mtime < int(since.timestamp()):
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as error:
            logger.debug("Журнал регистрации %s не прочитан: %s", path, error)
            continue
        for match in _ERROR_RECORD.finditer(text):
            if match.group(1) >= stamp:
                comment = match.group(2).replace('""', '"').replace("\r\n", "\n").strip()
                if comment:
                    errors.append(comment)
    return errors[-_MAX_ERRORS:]
