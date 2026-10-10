# onec-ops

CLI-утилита и Agent Skill для автоматизации пакетных операций 
1С:Предприятие. Работает как для человека в терминале, так и для 
ИИ-агентов (Codex, Claude Code).

## Статус

**Текущая версия: v0.2.3** (в разработке).

Реализовано:
- Кроссплатформенный запуск 1С (Linux DISPLAY / xvfb-run, Windows).
- `create-ib --type file` — создание файловой ИБ.
- `dump-config` / `load-config` — выгрузка и загрузка конфигурации в XML.
- `dump-cf` / `load-cf` — конфигурация `.cf` и расширения `.cfe` с `--extension`.
- `open-designer` / `open-enterprise` — открыть Конфигуратор или клиент 1С.

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

### Конфигурация в .cf

    onec-ops dump-cf --ib /path/to/ib --to /path/to/base.cf
    onec-ops load-cf --ib /path/to/ib --from /path/to/base.cf --update-db-cfg

### Расширения в .cfe

    onec-ops dump-cf --ib /path/to/ib --to /path/to/ext.cfe --extension Имя
    onec-ops load-cf --ib /path/to/ib --from /path/to/ext.cfe --extension Имя --update-db-cfg

Команды выгрузки создают родительские каталоги и предупреждают о перезаписи
существующего файла. Команды загрузки требуют существующий непустой файл.
Для файлов `.cfe` параметр `--extension Имя` обязателен; для `.cf` он запрещён.
Другие суффиксы допускаются с предупреждением. `.cfu` — обновление
конфигурации, его отдельная операция запланирована на v0.2.4.
`--update-db-cfg` обновляет конфигурацию БД после загрузки; без этого флага
передаётся только операция загрузки. Обе команды требуют `--ib`.

Для проверки команды без запуска 1С:

    onec-ops --ib /path/to/ib --dry-run dump-cf --to /tmp/base.cf
    onec-ops --ib /path/to/ib --dry-run load-cf --from /path/to/ext.cfe --extension Имя --update-db-cfg

Dry-run сохраняет проверки входного файла и ИБ. Для выгрузки он подготавливает
родительский каталог, но файл не создаёт. Подробности — в
[справочнике команд](references/commands.md).

### Открыть Конфигуратор или клиент 1С

    onec-ops open-designer --ib /path/to/ib
    onec-ops open-enterprise --ib /path/to/ib --user Администратор
    onec-ops open-enterprise --ib /path/to/ib --execute /path/to/task.epf --c "параметр"
    onec-ops open-designer --ib /path/to/ib --no-wait

В Linux GUI-команды требуют реальный работающий DISPLAY и недоступны в
headless-окружениях (CI, Docker, sandbox Codex). X-сервер проверяется через
`xdpyinfo`; если утилита отсутствует, выводится WARNING. При признаке sandbox
команда завершается с подсказкой выполнить её в терминале пользователя.
В Windows запуск выполняется напрямую в графической сессии, DISPLAY не нужен.

По умолчанию команда ждёт закрытия окна, с таймаутом 600 секунд (`--timeout`).
Флаг `--no-wait` запускает процесс через Popen и возвращает управление сразу;
stdout/stderr направляются в DEVNULL, в журнал записывается PID.
Обе команды принимают `--user` и `--password`; пароль маскируется в журнале команды.

    onec-ops --ib /path/to/ib --dry-run open-designer
    onec-ops --ib /path/to/ib --dry-run open-enterprise --execute ./task.epf --no-wait

Dry-run проверяет существующую ИБ, показывает команду с абсолютными путями,
пропускает проверки DISPLAY и sandbox и не запускает GUI.

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

### Настройка sandbox

В Linux-окружении с режимом `workspace-write` Codex может изолировать `/tmp`
через tmpfs, из-за чего Xvfb не запускается. Если диагностика подтверждает
эту причину, добавьте настройки для доверенного проекта в
`<путь-к-проекту>/.codex/config.toml`:

    sandbox_mode = "danger-full-access"
    approval_policy = "on-request"

Локальные настройки проекта загружаются только для доверенных проектов.
В `~/.codex/config.toml` таблица `[projects."<путь-к-проекту>"]` задаёт
`trust_level`; настройки sandbox размещайте в конфиге самого проекта.
См. [официальную документацию Codex](https://learn.chatgpt.com/docs/config-file/config-basic).

Или запустите Codex из каталога проекта с флагами:

    codex --sandbox danger-full-access --ask-for-approval on-request

**Внимание:** `danger-full-access` даёт Codex полный доступ к системе.
Используйте только для доверенных проектов. После изменения проверьте
применение настроек; если сессия сохраняет прежнюю изоляцию, начните новую.

Диагностика, проверка и ограничения:
[references/troubleshooting.md](references/troubleshooting.md).

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
