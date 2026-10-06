# onec-ops

CLI-утилита и Agent Skill для автоматизации пакетных операций 
1С:Предприятие. Работает как для человека в терминале, так и для 
ИИ-агентов (Codex, Claude Code).

## Статус

**Текущая версия: v0.2.0** (в разработке).

Реализовано:
- Кроссплатформенный запуск 1С (Linux DISPLAY / xvfb-run, Windows).
- `create-ib --type file` — создание файловой ИБ.
- `dump-config` / `load-config` — выгрузка и загрузка конфигурации в XML.

См. [roadmap.md](roadmap.md) для плана релизов.

## Требования

- **Python 3.11+**
- **Платформа 1С:Предприятие 8.3.x** (толстый клиент `1cv8`).
- **Linux**: `xvfb` — опционально, для headless-режима (CI, Docker).
- **Windows**: платформа 1С установлена стандартно.

### Важно про клиент 1С

Для пакетных операций Конфигуратора нужен **толстый клиент `1cv8`**. 
Тонкий клиент `1cv8c` **не поддерживает** `CREATEINFOBASE`, 
`DumpConfigToFiles`, `LoadConfigFromFiles`, `DumpIB` и работу 
с хранилищем, поэтому не подходит для автоматизации.

## Установка

### Для разработки

    git clone <repo-url>
    cd onec-ops
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"

### Для использования (планируется)

    pipx install onec-ops

## Использование

### Создание файловой ИБ

    onec-ops create-ib --type file --path /path/to/ib

Создаёт файловую информационную базу 1С в указанном каталоге. 
Если каталога нет — он будет создан.

### Перезапись существующей ИБ

По умолчанию `create-ib` не трогает существующую базу. Если нужно 
удалить её и создать заново:

    onec-ops create-ib --type file --path /path/to/ib --force

Команда запросит интерактивное подтверждение (нужно ввести `Y`). 
В неинтерактивной среде (CI, Docker) используйте явный флаг `--yes`:

    onec-ops create-ib --type file --path /path/to/ib --force --yes

### Выгрузка конфигурации в XML

    onec-ops dump-config --to /path/to/xml --ib /path/to/ib

По умолчанию используется формат `hierarchical`; для плоской структуры
добавьте `--format plain`. Каталог создаётся автоматически; если он
непустой, команда предупреждает о возможной перезаписи файлов.

### Загрузка конфигурации из XML

    onec-ops load-config --from /path/to/xml --ib /path/to/ib --update-db-cfg

Каталог должен существовать и содержать `Configuration.xml`. Флаг
`--update-db-cfg` обновляет конфигурацию БД после загрузки. Для обеих
команд `--ib` указывает на существующую файловую ИБ с `1Cv8.1CD`.

Для работы с одним расширением укажите `--extension NAME`, со всеми —
`--all-extensions`. Эти параметры взаимоисключающие. При загрузке одного
расширения наличие `Configuration.xml` не проверяется.

    onec-ops --ib /path/to/ib --dry-run dump-config --to /path/to/xml
    onec-ops --ib /path/to/ib --dry-run load-config --from /path/to/xml --update-db-cfg

Dry-run требует существующей ИБ и корректного каталога загрузки,
показывает команду с абсолютными путями и пропускает запуск 1С.
Подробнее: [справочник команд](references/commands.md).

### Общие параметры

Все команды поддерживают:

    --ib PATH              Путь к файловой ИБ (для команд конфигурации)
    --platform PATH        Путь к 1cv8 (по умолчанию — из конфига или ОС)
    --config PATH          Путь к TOML-конфигу
    --log-level LEVEL      DEBUG / INFO / WARNING / ERROR
    --log-file PATH        Файл журнала
    --dry-run              Показать команду без запуска 1С
    --timeout SEC          Таймаут запуска 1С (по умолчанию 600)

### Пример с dry-run

    onec-ops --dry-run create-ib --type file --path /tmp/test-ib

Показывает команду, но не запускает 1С.

## Использование с Codex

### Установка Skill

Codex требует реальные файлы (не symlinks) в ~/.codex/skills/:

    mkdir -p ~/.codex/skills/onec-ops
    cp SKILL.md ~/.codex/skills/onec-ops/
    cp -r agents ~/.codex/skills/onec-ops/
    cp -r references ~/.codex/skills/onec-ops/

Перезапустите Codex. В новом чате спросите "какие skills ты видишь?" —
в списке должен появиться onec-ops.

### Требования к окружению Codex

Codex должен работать БЕЗ sandbox, иначе X11 заблокирован и 1С
не запустится. Отключите sandbox в ~/.codex/config.toml:

    sandbox_mode = "danger-full-access"
    approval_policy = "on-request"

Или запускайте Codex с флагом:

    codex --dangerously-bypass-approvals-and-sandbox

**Внимание:** это даёт Codex полный доступ к системе. Используйте
только в доверенных средах.

### Пример

    Используй skill onec-ops, чтобы создать файловую базу 1С
    в /tmp/test-ib

Codex выполнит:

    onec-ops create-ib --type file --path /tmp/test-ib

## Разработка

    pytest -v              # тесты
    pytest --cov           # покрытие
    ruff check scripts tests  # линтер

Все unit-тесты мокают `subprocess.run` — реальные запуски 1С 
в тестах отсутствуют.

## Roadmap

См. [roadmap.md](roadmap.md).

## Лицензия

MIT — см. [LICENSE](LICENSE).
