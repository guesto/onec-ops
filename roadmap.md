# Roadmap onec-ops

CLI-утилита и Agent Skill для автоматизации пакетных операций 1С:Предприятие.

## Принципы

- **Итеративность.** Каждый релиз — маленький, проверяемый, с тестами.
- **Кроссплатформенность.** Linux + Windows, DISPLAY + xvfb-run.
- **Двойное назначение.** Утилита работает и для человека (CLI), 
  и для ИИ-агента (Agent Skill).

## Состояние

**Текущий релиз:** v0.2.1 [В РАБОТЕ].
**Завершённые:** v0.1.0 [ГОТОВО], v0.2.0 [ГОТОВО].

---

## Завершённые релизы

### v0.1.0 — Фундамент: дисплей + файловая ИБ [ГОТОВО]

**Дата:** 2026-10-03

- Кроссплатформенный `runner` (Linux DISPLAY / xvfb-run, Windows direct).
- Проверка окружения: `DISPLAY`, `xvfb-run`, платформа 1С.
- Команда `create-ib --type file --path <path>` — создание файловой ИБ.
- Безопасный `--force`: интерактивное подтверждение Y/n, `--yes` для CI.
- Таймаут 600 с, UTF-8-декодирование, маскирование паролей.
- `xvfb-run -a -s "-nolisten unix"` — работа без прав root.
- Unit-тесты: 20 passed, покрытие 71%.
- Agent Skill: `SKILL.md`, `agents/openai.yaml`, `references/commands.md`.
- Установка через `pipx` как глобальная команда `onec-ops`.
- Skill протестирован в Codex (end-to-end, создание ИБ).
- Документация по sandbox-режиму Codex.

**Известные ограничения:**
- Codex в sandbox-режиме не может запускать 1С (X11 заблокирован).
  Решение: `sandbox_mode = "danger-full-access"` в `~/.codex/config.toml`.
- `create-ib --type server` — заглушка (v0.1.1).

---

## Планируемые релизы

### v0.1.1 — Клиент-серверная ИБ [ОТЛОЖЕНО]

**Причина:** требуется установленный и запущенный сервер 1С, 
которого сейчас нет. Реализация без возможности проверить на реальной 
среде бессмысленна.

**Условия возобновления:**
- Появится доступ к серверу 1С (`ragent`, `rmngr`, `rphost`).
- Или возникнет практическая задача, требующая клиент-серверной ИБ.

**Планируемое содержание:**
- Проверка наличия сервера 1С.
- Команда `create-ib --type server --server <srv> --ref <name>`.
- Документация по подготовке серверной среды.
- Unit-тесты с моками.

**Не блокирует** другие релизы.

### v0.2.0 — Конфигурация (XML) [ГОТОВО]

**Приоритет:** высокий.

- `dump-config` — выгрузка конфигурации в XML.
  - `--format hierarchical|plain`
  - `--extension <имя>`, `--all-extensions`
- `load-config` — загрузка конфигурации из XML.
  - `--from <каталог>`
  - `--update-db-cfg` (флаг)
- Round-trip тест.
- Unit-тесты для validate и build_1c_args.
- Skill: разделы `dump-config` / `load-config`.
- README: примеры.

### v0.2.1 — Файловые форматы (.cf / .cfu) [В РАБОТЕ]

**Приоритет:** высокий.

- `dump-cf` — выгрузка конфигурации в `.cf` (`/DumpCfg`).
- `load-cf` — загрузка конфигурации из `.cf` (`/LoadCfg`).
- `dump-cfu` — выгрузка расширения в `.cfu` (`/DumpCfg -Extension`).
- `load-cfu` — загрузка расширения из `.cfu` (`/LoadCfg -Extension`).
- Round-trip тесты.
- Skill: четыре новые команды.

### v0.2.2 — GUI: открытие клиентов [ПЛАНИРУЕТСЯ]

**Приоритет:** средний.

- `open-designer` — открыть Конфигуратор (`DESIGNER /F <ib>`).
- `open-enterprise` — открыть клиент 1С (`ENTERPRISE /F <ib>`).
- Опции: `--user`, `--password`, `--execute`, `--c`, `--no-wait`.
- Особенность: команды **ждут закрытия окна** (если не `--no-wait`).
- Skill: разделы про GUI с оговоркой, что **требуется DISPLAY**.

### v0.3.0 — Внешние обработки (XML) [ПЛАНИРУЕТСЯ]

**Приоритет:** высокий.

- `load-epf` — сборка `.epf` из XML.
  - `/LoadExternalDataProcessorOrReportFromFiles`
- `dump-epf` — разборка `.epf` в XML.
  - `/DumpExternalDataProcessorOfReportToFiles`
- Round-trip тест.
- Учёт ограничений платформы 8.5.1.1343 (если `dump-epf` требует GUI).
- Skill: разделы `load-epf` / `dump-epf`.

### v0.4.0 — Бэкапы базы (DT) [ПЛАНИРУЕТСЯ]

**Приоритет:** средний.

- `dump-dt` — выгрузка базы в `.dt` (`/DumpIB`).
- `restore-dt` — восстановление из `.dt` (`/RestoreIB`).
- Round-trip тест.

### v0.5.0 — Хранилище конфигурации [ПЛАНИРУЕТСЯ]

**Приоритет:** средний.

- `repo-create` — создание хранилища (`/ConfigurationRepositoryCreate`).
- `repo-bind` — подключение базы к хранилищу (`/ConfigurationRepositoryBindCfg`).
- `repo-update` — обновление из хранилища (`/ConfigurationRepositoryUpdateCfg`).
- `repo-add-user` — добавление пользователя (`/ConfigurationRepositoryAddUser`).
- Разделение аутентификации: ИБ (`/N`, `/P`) vs хранилище 
  (`/ConfigurationRepositoryN`, `/ConfigurationRepositoryP`).
- Skill: четыре новые команды.

### v0.6.0 — Расширения [ПЛАНИРУЕТСЯ]

**Приоритет:** средний.

- `load-extension` — загрузка `.cfe` в ИБ (`/LoadCfg`).
- `dump-extension` — выгрузка расширения в XML.
- `load-extension-xml` — загрузка расширения из XML.
- Skill: три новые команды.

### v0.7.0 — Обновление конфигурации БД [ПЛАНИРУЕТСЯ]

**Приоритет:** низкий.

- `update-db` — обновление конфигурации БД (`/UpdateDBCfg`).
- Поддержка `--dynamic` для динамического обновления.

### v0.8.0 — Полировка Skill [ПЛАНИРУЕТСЯ]

**Приоритет:** средний.

- Финальная редакция `SKILL.md` с учётом всех команд.
- `references/` с детальными описаниями каждой команды.
- `references/troubleshooting.md` — типичные ошибки и решения.
- Проверка Skill в Codex и Claude Code.
- Symlinks в `.agents/skills/` и `.claude/skills/`.
- Документация по установке Skill для разных агентов.

### v0.9.0 — CI/CD и публикация [ПЛАНИРУЕТСЯ]

**Приоритет:** высокий перед v1.0.

- GitHub Actions: тесты на Linux + Windows, Python 3.11–3.14.
- `ruff check` + `ruff format` в CI.
- Pre-commit hooks.
- Покрытие тестами ≥ 80%.
- Публикация в PyPI (`pipx install onec-ops`).
- CHANGELOG.md.
- CONTRIBUTING.md.

### v1.0.0 — Стабильный релиз [ПЛАНИРУЕТСЯ]

**Приоритет:** цель.

- Документация полная: README, CHANGELOG, CONTRIBUTING, SECURITY.
- Все команды проверены на реальной 1С.
- Skill протестирован в Codex и Claude Code.
- Семантическое версионирование, стабильный API.
- Поддержка Linux и Windows.
- Опубликован в PyPI.

---

## Технические решения (накопленные)

### Запуск 1С

- **Толстый клиент `1cv8`** для всех пакетных операций. Тонкий `1cv8c` 
  не поддерживает `CREATEINFOBASE` и большинство операций Конфигуратора.
- **Linux + DISPLAY** — прямой запуск `1cv8`.
- **Linux без DISPLAY + xvfb-run** — `xvfb-run -a -s "-nolisten unix" 1cv8`.
- **Linux без DISPLAY и без xvfb-run** — ошибка `XvfbNotAvailable`.
- **Windows** — прямой запуск `1cv8.exe`.

### Agent Skill

- Канонический `SKILL.md` в корне проекта.
- Установка в Codex через **копирование** (не symlinks) 
  в `~/.codex/skills/onec-ops/`.
- Установка в Claude Code через `~/.claude/skills/onec-ops/`.
- Skill наполняется постепенно, по мере роста команд.

### Codex и sandbox

- В sandbox-режиме Codex X11 заблокирован, 1С не запускается.
- Решение: `sandbox_mode = "danger-full-access"` в `~/.codex/config.toml`.
- Skill документирует это ограничение и не пытается обойти.

### Установка

- **Для разработки:** `pip install -e ".[dev]"` в venv.
- **Для использования:** `pipx install --editable <путь>`.
- **Для публикации (v0.9.0):** `pipx install onec-ops` из PyPI.

---

## Вне scope

- Windows-специфичные фичи (COM-интеграция и т.п.).
- Работа с кластером серверов 1С через `ras`/`rac`.
- Публикация на веб-сервере.
- GUI.
- Работа в sandbox-режиме Codex (задокументировано как ограничение).