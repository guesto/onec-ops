"""Запуск платформы 1С."""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .exceptions import OneCFailed, PlatformNotFound, XvfbNotAvailable

logger = logging.getLogger(__name__)
_PASSWORD_OPTIONS = {"/p", "/configurationrepositoryp", "-pwd"}
_OUT_MODES = {"DESIGNER", "CREATEINFOBASE"}
_TERMINATE_GRACE = 5.0


@dataclass
class RunContext:
    """Параметры запуска платформы 1С."""

    platform_path: Path
    log_file: Path | None = None
    log_level: str = "INFO"
    dry_run: bool = False
    timeout: int = 600
    requires_gui: bool = False


class OneCCompletedProcess(subprocess.CompletedProcess[str]):
    """Результат запуска 1С с текстом файла /Out."""

    out_text: str = ""


def _check_platform(platform_path: Path) -> None:
    """Проверяет, что исполняемый файл платформы доступен."""
    if not platform_path.exists() or (sys.platform != "win32" and not os.access(platform_path, os.X_OK)):
        raise PlatformNotFound(f"Платформа 1С не найдена или не исполняема: {platform_path}")


def build_command(args: list[str], ctx: RunContext) -> list[str]:
    """Собирает команду запуска 1С с учётом окружения."""
    _check_platform(ctx.platform_path)
    platform = str(ctx.platform_path)

    if sys.platform == "win32" or ctx.requires_gui or os.environ.get("DISPLAY"):
        return [platform, *args]

    if shutil.which("xvfb-run"):
        # -a: автоматический выбор дисплея.
        # -s "-nolisten unix": не создавать сокет в /tmp/.X11-unix,
        # чтобы не требовать прав root (см. проблему с euid != 0).
        return ["xvfb-run", "-a", "-s", "-nolisten unix", platform, *args]

    raise XvfbNotAvailable("Нет DISPLAY и не найден xvfb-run. Установите xvfb или задайте DISPLAY.")


def _mask_passwords(command: list[str]) -> list[str]:
    """Возвращает копию команды без паролей."""
    masked = list(command)
    for index, value in enumerate(masked[:-1]):
        if value.lower() in _PASSWORD_OPTIONS:
            masked[index + 1] = "***"
    return masked


def _kill_process_group(process: subprocess.Popen[str]) -> None:
    """Завершает процесс 1С вместе с его группой (xvfb-run, Xvfb, 1cv8).

    Сначала SIGTERM, чтобы Xvfb удалил свой lock-файл, затем SIGKILL тем,
    кто не завершился за _TERMINATE_GRACE секунд.
    """
    if sys.platform == "win32":
        process.kill()
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + _TERMINATE_GRACE
    while time.monotonic() < deadline:
        process.poll()
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _execute(command: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    """Запускает 1С в отдельной группе процессов и ждёт завершения.

    subprocess.run при таймауте убивает только прямого потомка: под xvfb-run
    это обёртка, а 1cv8 и Xvfb остались бы работать и держать ИБ.
    Поэтому при таймауте и любом прерывании завершается вся группа.
    """
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=sys.platform != "win32",
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except BaseException:
            _kill_process_group(process)
            process.wait()
            raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def _find_out_file(args: list[str]) -> Path | None:
    """Возвращает файл из ключа /Out, если он уже передан."""
    for index, value in enumerate(args[:-1]):
        if value.lower() == "/out":
            return Path(args[index + 1])
    return None


def _read_out_file(out_file: Path | None) -> str:
    """Читает файл /Out (1С пишет UTF-8 с BOM); отсутствие файла не ошибка."""
    if out_file is None:
        return ""
    try:
        return out_file.read_text(encoding="utf-8-sig", errors="replace").strip()
    except OSError:
        return ""


def _with_out_text(message: str, out_text: str) -> str:
    """Добавляет сообщения 1С к тексту ошибки."""
    return f"{message}\n{out_text}" if out_text else message


def run_1c(args: list[str], ctx: RunContext) -> OneCCompletedProcess:
    """Запускает 1С и преобразует ошибки процесса в OneCFailed.

    Для пакетных DESIGNER/CREATEINFOBASE добавляет /Out во временный файл:
    иначе текст ошибки 1С недоступен (stdout и stderr пустые).
    """
    out_file = _find_out_file(args)
    temp_out_file: Path | None = None
    if (
        out_file is None
        and not ctx.dry_run
        and not ctx.requires_gui
        and args
        and args[0].upper() in _OUT_MODES
    ):
        fd, name = tempfile.mkstemp(prefix="onec-ops-out-", suffix=".txt")
        os.close(fd)
        temp_out_file = out_file = Path(name)
        args = [*args, "/Out", name]
    try:
        return _run_1c(args, ctx, out_file)
    finally:
        if temp_out_file is not None:
            temp_out_file.unlink(missing_ok=True)


def _run_1c(
    args: list[str], ctx: RunContext, out_file: Path | None,
) -> OneCCompletedProcess:
    command = build_command(args, ctx)
    logged_command = _mask_passwords(command)
    logger.info("Команда 1С: %s", logged_command)

    if ctx.dry_run:
        logger.info("Dry-run: запуск 1С пропущен")
        return OneCCompletedProcess(command, 0, "", "")

    started_at = time.monotonic()
    try:
        result = _execute(command, timeout=ctx.timeout)
    except subprocess.TimeoutExpired as error:
        duration = time.monotonic() - started_at
        logger.error("1С превысила таймаут за %.2f с: %s", duration, logged_command)
        out_text = _read_out_file(out_file)
        raise OneCFailed(
            _with_out_text(
                f"1С не завершилась за {ctx.timeout} секунд. Возможные причины: "
                "открыт диалог, отсутствует база, проблемы с лицензией.",
                out_text,
            ),
            returncode=-1,
            command=command,
            stderr=str(error),
        ) from error
    except OSError as error:
        raise OneCFailed(
            f"Не удалось запустить 1С: {error}",
            returncode=-1, command=command, stderr=str(error),
        ) from error

    duration = time.monotonic() - started_at
    logger.info("stdout 1С: %s", result.stdout)
    logger.info("stderr 1С: %s", result.stderr)
    out_text = _read_out_file(out_file)
    if out_text:
        logger.info("Сообщения 1С (/Out): %s", out_text)
    logger.info("1С завершилась с кодом %s за %.2f с", result.returncode, duration)

    if result.returncode != 0:
        raise OneCFailed(
            _with_out_text(f"1С завершилась с ненулевым кодом: {result.returncode}", out_text),
            returncode=result.returncode,
            command=command,
            stderr=result.stderr,
        )

    completed = OneCCompletedProcess(result.args, result.returncode, result.stdout, result.stderr)
    completed.out_text = out_text
    return completed


def _verify_display(display: str) -> bool:
    """Проверяет X-сервер через xdpyinfo; отсутствие утилиты не блокирует запуск."""
    xdpyinfo = shutil.which("xdpyinfo")
    if not xdpyinfo:
        logger.warning("xdpyinfo не найден — проверка DISPLAY пропущена")
        return True
    try:
        result = subprocess.run(
            [xdpyinfo, "-display", display], capture_output=True, timeout=5, check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _detect_codex_sandbox() -> bool:
    """Определяет возможную песочницу по владельцу /tmp/.X11-unix."""
    x11_dir = Path("/tmp/.X11-unix")
    try:
        return x11_dir.exists() and x11_dir.stat().st_uid != 0
    except OSError:
        return False


def run_1c_popen(args: list[str], ctx: RunContext) -> subprocess.Popen | None:
    """Запускает 1С без ожидания; при dry-run возвращает None."""
    command = build_command(args, ctx)
    logger.info("Команда 1С (Popen): %s", _mask_passwords(command))
    if ctx.dry_run:
        logger.info("Dry-run: запуск 1С пропущен")
        return None
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError as error:
        raise OneCFailed(
            f"Не удалось запустить 1С: {error}",
            returncode=-1, command=command, stderr=str(error),
        ) from error
    logger.info("1С запущена в фоне, PID: %s", process.pid)
    return process
