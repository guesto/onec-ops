# Changelog

Все значимые изменения в проекте onec-ops.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).
Проект использует [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Планируется

- v0.2.0 — dump-config / load-config (выгрузка и загрузка конфигурации в XML).

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

[Unreleased]: https://github.com/guesto/onec-ops/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/guesto/onec-ops/releases/tag/v0.1.0
