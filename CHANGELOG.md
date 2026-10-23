# Changelog

Все значимые изменения в проекте onec-ops.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).
Проект использует [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

## [0.8.3] — 2026-10-24

### Fixed

- Пустой или состоящий из пробелов `--extension` отклоняется в командах
  `dump-config`, `load-config`, `dump-cf` и `load-cf`, вместо молчаливого выбора
  основной конфигурации или передачи пустого имени платформе.
- Относительный путь к платформе из CLI, окружения или TOML приводится
  к абсолютному: `--platform ./1cv8` больше не ищет файл через `PATH`.
- Каталог больше не принимается за исполняемый файл платформы, в том числе
  при `--dry-run`.
- Ошибки открытия журнала и подготовки каталога новой ИБ выводятся
  понятным сообщением с кодом 1 вместо Python traceback.

### Added

- 19 регрессионных проверок валидации аргументов, путей платформы и файловых
  ошибок; всего 506 тестов, покрытие 98%.

## [0.8.2] — 2026-10-23

### Fixed

- `load-config --all-extensions` принимает каталог, созданный
  `dump-config --all-extensions`: `Configuration.xml` находится в подкаталогах
  расширений и больше не требуется в корне.
- Ошибки чтения и разбора TOML-конфига, а также неверный тип `platform`
  выводятся с путём файла и кодом 1 вместо Python traceback.

### Changed

- Версия Python-пакета синхронизирована с релизом: `0.8.2`.

### Added

- 8 регрессионных проверок загрузки всех расширений и некорректного конфига;
  всего 487 тестов, покрытие 98%.

## [0.8.1] — 2026-10-23

### Fixed

- При таймауте и Ctrl+C оставались работать `1cv8` и `Xvfb` (убивалась только
  обёртка `xvfb-run`), зависший `1cv8` держал ИБ. Теперь 1С запускается в своей
  группе процессов, и завершается вся группа.
- Ошибка запуска платформы (`OSError`) выводилась трейсбеком — теперь
  «Не удалось запустить 1С: …».
- README и `references/commands.md` обещали `.cfu` в несуществующем релизе v0.2.4.

### Added

- Тесты выбора платформы: `--platform` → `ONEC_OPS_PLATFORM` → конфиг → по умолчанию.

## [0.7.0] — 2026-10-23

Выпущен после 0.8.0.

### Added

- Команда `update-db` — применение загруженной конфигурации к БД (`/UpdateDBCfg`):
  `--extension` / `--all-extensions`, `--dynamic` / `--no-dynamic`, `--warnings-as-errors`.
- Skill: `update-db` в списке разрушающих команд; после `repo-bind` / `repo-update` —
  `update-db`; сценарий «Изменения из хранилища в БД».

## [0.8.0] — 2026-10-23

### Changed

- `SKILL.md` переписан: `description` со всеми группами операций, правила
  безопасности для агента, коды возврата, таблица всех команд с `--ib`.
- Пакет навыка самодостаточен: ссылки только на `references/`.
- `references/commands.md`: оглавление, общие параметры, коды возврата.
- `references/troubleshooting.md`: оглавление и разделы о платформе,
  дисплее, таймауте, подтверждении, расширениях.
- README: установка навыка в Claude Code и Codex, обновление копий,
  установка утилиты через pipx из GitHub.

### Added

- `references/workflows.md` — типовые сценарии.
- `tests/test_skill.py` — проверка дрейфа между CLI и навыком.

### Fixed

- `create-ib --force --dry-run` удалял существующую ИБ: dry-run больше не удаляет каталог.
- Сообщение о `--type server` ссылалось на несуществующий релиз v0.1.1.

## [0.6.0] — 2026-10-23

### Added

- Команда `list-extensions` — список расширений ИБ в stdout.
- Команда `check-extension` — проверка, можно ли применить расширение.
- Команда `delete-extension` — удаление расширения с подтверждением (`--yes` для CI).
- `run_1c` возвращает текст `/Out` (`OneCCompletedProcess.out_text`).

## [0.5.3] — 2026-10-23

### Added

- Общие параметры `--ib-user` / `--ib-password` — пользователь ИБ (`/N`, `/P`)
  для всех команд с `--ib`, включая пакетные.
- Переменные окружения `ONEC_OPS_IB_USER` / `ONEC_OPS_IB_PASSWORD`.

### Deprecated

- `--user` / `--password` у `open-designer` и `open-enterprise` — используйте
  `--ib-user` / `--ib-password`.

## [0.5.2] — 2026-10-22

### Added

- Сообщения 1С из `/Out` в журнале и в тексте ошибки CLI: пакетные `DESIGNER`/`CREATEINFOBASE`
  получают `/Out <временный файл>` (UTF-8 с BOM), файл удаляется после запуска.

## [0.5.1] — 2026-10-22

### Added

- Команда `repo-add-user` — добавление пользователя в хранилище конфигурации.
- Опции: `--rights`, `--password`, `--restore-deleted`.
- Маскирование пароля `-Pwd` в журнале команды.

## [0.5.0] — 2026-10-20

### Added

- Команда `repo-create` — создание хранилища конфигурации.
- Команда `repo-bind` — подключение базы к хранилищу.
- Команда `repo-update` — обновление из хранилища.

### Known Limitations

- Только файловое хранилище (без `crserver`, tcp://, http://).
- Один пользователь хранилища = одна база (`repo-add-user` — v0.5.1).

## [0.4.0] — 2026-10-19

### Added

- Команда `dump-dt` — выгрузка базы в .dt.
- Команда `restore-dt` — восстановление базы из .dt.
- Опции: --force, --yes для безопасного восстановления.

## [0.3.0] — 2026-10-11

### Added

- Команда `dump-epf` — разборка внешней обработки/отчёта .epf/.erf в XML.
- Команда `load-epf` — сборка внешней обработки/отчёта .epf/.erf из XML.

## [0.2.3] — 2026-10-10

### Added

- Команда `open-designer` — открыть Конфигуратор 1С.
- Команда `open-enterprise` — открыть клиент 1С.
- Опции: `--user`, `--password`, `--no-wait`.
- Для `open-enterprise`: `--execute`, `--c`.
- Проверки DISPLAY через xdpyinfo и признака sandbox Codex; запуск через Popen.

## [0.2.2] — 2026-10-06

### Changed

- `dump-cf` и `load-cf` работают с конфигурацией `.cf` и расширениями `.cfe` через `--extension`.
- Для `.cfe` требуется `--extension`; для `.cf` эта опция запрещена. Другие суффиксы вызывают WARNING.
- Исправлена семантика форматов: `.cfu` — обновление конфигурации, `.cfe` — расширение.

### Removed

- Команды `dump-cfu` и `load-cfu`, их действия и тесты.

## [0.2.1] — 2026-10-06

### Added

- Команда `dump-cf` — выгрузка конфигурации в .cf.
- Команда `load-cf` — загрузка конфигурации из .cf.
- Команда `dump-cfu` — выгрузка расширения в .cfu.
- Команда `load-cfu` — загрузка расширения из .cfu.

## [0.2.0] — 2026-10-06

### Added

- Команда `dump-config` — выгрузка конфигурации в XML.
- Команда `load-config` — загрузка конфигурации из XML.
- Опции `--format`, `--extension`, `--all-extensions`, `--update-db-cfg`.
- Общий параметр `--ib` и проверка существующей файловой ИБ.

## [0.1.0] — 2026-10-03

### Added

- Кроссплатформенный runner (Linux DISPLAY/xvfb-run, Windows direct).
- Команда `create-ib --type file` — создание файловой ИБ.
- Безопасный `--force` с интерактивным подтверждением Y/n.
- Флаг `--yes` для неинтерактивной среды (CI).
- Проверка окружения: DISPLAY, xvfb-run, платформа 1С.
- Таймаут 600 с, UTF-8-декодирование, маскирование паролей.
- `xvfb-run -a -s "-nolisten unix"` для работы без прав root.
- Agent Skill: SKILL.md, agents/openai.yaml, references/commands.md.
- Установка через pipx как глобальная команда `onec-ops`.
- 20 unit-тестов, покрытие 73%.

### Known Limitations

- Codex в sandbox-режиме не может запускать 1С (X11 заблокирован).
  Решение: `sandbox_mode = "danger-full-access"` в `~/.codex/config.toml`.
- `create-ib --type server` — заглушка (v0.1.1 отложен).

[Unreleased]: https://github.com/guesto/onec-ops/compare/v0.8.3...HEAD
[0.8.3]: https://github.com/guesto/onec-ops/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/guesto/onec-ops/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/guesto/onec-ops/compare/v0.7.0...v0.8.1
[0.7.0]: https://github.com/guesto/onec-ops/compare/v0.8.0...v0.7.0
[0.8.0]: https://github.com/guesto/onec-ops/compare/v0.6.0...v0.8.0
[0.6.0]: https://github.com/guesto/onec-ops/compare/v0.5.3...v0.6.0
[0.5.3]: https://github.com/guesto/onec-ops/compare/v0.5.2...v0.5.3
[0.5.2]: https://github.com/guesto/onec-ops/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/guesto/onec-ops/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/guesto/onec-ops/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/guesto/onec-ops/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/guesto/onec-ops/compare/v0.2.3...v0.3.0
[0.2.3]: https://github.com/guesto/onec-ops/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/guesto/onec-ops/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/guesto/onec-ops/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/guesto/onec-ops/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/guesto/onec-ops/releases/tag/v0.1.0
