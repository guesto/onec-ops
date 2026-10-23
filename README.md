# onec-ops

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/guesto/onec-ops/actions/workflows/test.yml/badge.svg)](https://github.com/guesto/onec-ops/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/guesto/onec-ops?include_prereleases&label=release)](https://github.com/guesto/onec-ops/releases)

CLI-утилита и Agent Skill для автоматизации пакетных операций 
1С:Предприятие. Работает как для человека в терминале, так и для 
ИИ-агентов (Codex, Claude Code).

## Статус

**Текущая версия: v0.6.0** (2026-10-23).

Реализовано:
- Кроссплатформенный запуск 1С (Linux DISPLAY / xvfb-run, Windows).
- `create-ib --type file` — создание файловой ИБ.
- `dump-config` / `load-config` — выгрузка и загрузка конфигурации в XML.
- `dump-cf` / `load-cf` — конфигурация `.cf` и расширения `.cfe` с `--extension`.
- `open-designer` / `open-enterprise` — открыть Конфигуратор или клиент 1С.
- `dump-epf` / `load-epf` — разборка и сборка внешних обработок `.epf` и отчётов `.erf` в XML.
- `dump-dt` / `restore-dt` — резервное копирование и восстановление базы через `.dt`.
- `repo-create` / `repo-bind` / `repo-update` / `repo-add-user` — файловое хранилище конфигурации.
- `list-extensions` / `check-extension` / `delete-extension` — список, проверка и удаление расширений.

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

### Для использования

    pipx install git+https://github.com/guesto/onec-ops.git

Обновление до последней версии из `main`:

    pipx install --force git+https://github.com/guesto/onec-ops.git

Публикация в PyPI (`pipx install onec-ops`) запланирована в v0.9.0.

### Для разработки

    git clone https://github.com/guesto/onec-ops.git
    cd onec-ops
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"

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

Список, проверка и удаление расширений:

    onec-ops list-extensions --ib /path/to/ib
    onec-ops check-extension --ib /path/to/ib --extension Имя
    onec-ops delete-extension --ib /path/to/ib --extension Имя

`list-extensions` печатает имена в stdout по одному в строке. `check-extension`
(`--extension Имя` или `--all-extensions`) не меняет ИБ: код 0 — расширение
можно применить, код 1 — причины 1С в выводе. `delete-extension` удаляет
расширение вместе с данными его объектов и требует подтверждения `Y`;
`--yes` — без вопроса (CI).

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
    onec-ops open-enterprise --ib /path/to/ib --ib-user Администратор
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
Пользователь ИБ задаётся общими `--ib-user` / `--ib-password` (см. «Пользователь ИБ»);
прежние `--user` / `--password` у этих команд работают, но устарели.

    onec-ops --ib /path/to/ib --dry-run open-designer
    onec-ops --ib /path/to/ib --dry-run open-enterprise --execute ./task.epf --no-wait

Dry-run проверяет существующую ИБ, показывает команду с абсолютными путями,
пропускает проверки DISPLAY и sandbox и не запускает GUI.

### Внешние обработки и отчёты (.epf / .erf)

    onec-ops dump-epf --ib /path/to/ib --epf /path/to/file.epf --to /path/to/xml
    onec-ops load-epf --ib /path/to/ib --root /path/to/xml/file.xml --epf /path/to/file.epf

Для отчётов используйте те же команды с файлом `.erf`:

    onec-ops dump-epf --ib /path/to/ib --epf /path/to/report.erf --to /path/to/report-xml
    onec-ops load-epf --ib /path/to/ib --root /path/to/report-xml/report.xml --epf /path/to/report.erf

`dump-epf` требует существующий непустой файл `.epf` или `.erf` (регистр
суффикса не важен). Каталог XML создаётся автоматически; при непустом
каталоге выводится WARNING о возможной перезаписи.
`load-epf` принимает корневой непустой `.xml` и создаёт родительские каталоги
для выходного файла. Каталоги назначения проверяются на доступность записи.
Обе команды требуют существующую файловую ИБ с `1Cv8.1CD` и поддерживают dry-run:

    onec-ops --ib /path/to/ib --dry-run dump-epf --epf /path/to/file.epf --to /tmp/epf-dump
    onec-ops --ib /path/to/ib --dry-run load-epf --root /path/to/file.xml --epf /tmp/test.epf

Dry-run выполняет валидацию и подготавливает каталоги, но не создаёт XML или
файл обработки. Для `load-epf` нужен уже существующий корневой XML-файл.

### Бэкап и восстановление базы (.dt)

    onec-ops dump-dt --ib /path/to/ib --to /path/to/backups/base.dt
    onec-ops restore-dt --ib /path/to/ib --from /path/to/backups/base.dt

Обе команды требуют существующую файловую ИБ с `1Cv8.1CD`.
`dump-dt` создаёт родительские каталоги, если их нет, и предупреждает
о перезаписи существующего файла. Расширение, отличное от `.dt`, вызывает WARNING.
`restore-dt` требует существующий непустой файл с расширением `.dt`.

Восстановление перезаписывает данные и конфигурацию целевой ИБ.
Без `--force` и с одним `--force` команда запрашивает подтверждение `Y`.
Для CI используйте оба флага `--force --yes`:

    onec-ops restore-dt --ib /path/to/ib --from /path/to/backups/base.dt --force --yes

В non-TTY без этой пары флагов восстановление завершается ошибкой.
Флаг `--yes` без `--force` не отменяет запрос подтверждения.

    onec-ops --ib /path/to/ib --dry-run dump-dt --to /tmp/backup.dt
    onec-ops --ib /path/to/ib --dry-run restore-dt --from /tmp/backup.dt --force --yes

Dry-run проверяет ИБ и пути, для выгрузки создаёт родительские каталоги,
но не создаёт `.dt` и не запускает 1С. Для dry-run восстановления нужен
уже существующий непустой `.dt`; подтверждение действует так же, как при запуске.

### Файловое хранилище конфигурации

    onec-ops repo-create --ib /path/to/ib --storage /path/to/storage
    onec-ops repo-bind --ib /path/to/other-ib --storage /path/to/storage --storage-user Администратор
    onec-ops repo-update --ib /path/to/other-ib --storage /path/to/storage --storage-user Администратор
    onec-ops repo-add-user --ib /path/to/ib --storage /path/to/storage --storage-user Администратор --user Разработчик2 --rights LockObjects

Все команды хранилища требуют существующую файловую ИБ с `1Cv8.1CD`.
`repo-create` создаёт каталог хранилища вместе с недостающими родительскими
каталогами и предупреждает, если он уже непустой. Администратор по умолчанию —
«Администратор»; для других учётных данных задайте `--user NAME --password PWD`.

`repo-bind` требует существующий непустой каталог хранилища. Флаг `--force`
передаёт `-forceReplaceCfg` и разрешает перезапись конфигурации базы.
`repo-update` требует существующий каталог и по умолчанию получает последнюю
версию; `--version N` выбирает версию, `--force` получает новые объекты.
Для обеих команд учётные данные задаются опциональными `--storage-user NAME`
и `--storage-password PWD`. Пароль маскируется в журнале команды.

`repo-add-user` добавляет пользователя от имени администратора хранилища
(`--storage-user` / `--storage-password`). `--rights` обязателен: `ReadOnly`,
`LockObjects`, `ManageConfigurationVersions` или `Administration`;
`--password` задаёт пароль нового пользователя, `--restore-deleted`
восстанавливает удалённого. Одного пользователя можно подключить только
к одной базе, поэтому для каждой следующей базы заведите своего пользователя.
`--ib` должна быть подключена к этому хранилищу или не подключена ни к какому.

    onec-ops repo-update --ib /path/to/other-ib --storage /path/to/storage --version 5 --force
    onec-ops --ib inputs/base1c --dry-run repo-create --storage inputs/storage1c
    onec-ops --ib inputs/base1c --dry-run repo-bind --storage inputs/storage1c --storage-user admin
    onec-ops --ib inputs/base1c --dry-run repo-update --storage inputs/storage1c

Dry-run проверяет ИБ и пути, показывает команду с абсолютными путями, но
не запускает 1С. Для `repo-create` он создаёт только каталог: для последующего
`repo-bind` нужно уже существующее непустое хранилище.
Поддерживается только файловое хранилище, без `crserver` и удалённых адресов.
Подробнее: [справочник команд](references/commands.md#repo-create).

### Общие параметры

Все команды поддерживают:

    --ib PATH              Существующая файловая ИБ (для всех команд, кроме create-ib)
    --ib-user NAME         Пользователь ИБ (/N) для всех команд с --ib
    --ib-password PWD      Пароль пользователя ИБ (/P)
    --platform PATH        Путь к 1cv8 (по умолчанию — из конфига или ОС)
    --config PATH          Путь к TOML-конфигу
    --log-level LEVEL      DEBUG / INFO / WARNING / ERROR
    --log-file PATH        Файл журнала
    --dry-run              Показать команду без запуска 1С
    --timeout SEC          Таймаут запуска 1С (по умолчанию 600)

### Пользователь ИБ

Если в ИБ есть пользователи, передайте пользователя для любой команды с `--ib`:

    onec-ops --ib /path/to/ib --ib-user Пользователь --ib-password secret dump-cf --to /tmp/base.cf

Пароль удобнее передавать через окружение — он не попадёт в историю shell:

    export ONEC_OPS_IB_USER=Пользователь
    export ONEC_OPS_IB_PASSWORD=secret
    onec-ops --ib /path/to/ib dump-config --to /tmp/xml

Параметры CLI важнее переменных окружения. Без пользователя 1С отвечает
«Пользователь ИБ не идентифицирован» (код 1) — даже если у пользователя нет
пароля. У `repo-create` и `repo-add-user` параметры `--user` / `--password`
означают пользователя хранилища, а не ИБ.

### Пример с dry-run

    onec-ops --dry-run create-ib --type file --path /tmp/test-ib

Показывает команду, но не запускает 1С.

## Agent Skill

Навык учит агента (Claude Code, Codex) пользоваться `onec-ops`: какую
команду выбрать, какие команды разрушают данные, как читать ошибки 1С.
Утилиту `onec-ops` устанавливайте отдельно (см. «Установка»).

Пакет навыка — три пути, которые устанавливаются вместе:

    SKILL.md        # точка входа
    references/     # commands.md, workflows.md, troubleshooting.md
    agents/         # метаданные для Codex (openai.yaml)

Ссылки в `SKILL.md` ведут только в `references/`, поэтому навык работает
и в копии, отдельно от репозитория.

### Claude Code — в проекте onec-ops

Каталог `.claude/` не хранится в git. После `git clone` создайте ссылки:

    mkdir -p .claude/skills/onec-ops
    ln -sfn ../../../SKILL.md .claude/skills/onec-ops/SKILL.md
    ln -sfn ../../../references .claude/skills/onec-ops/references
    ln -sfn ../../../agents .claude/skills/onec-ops/agents

Ссылки на `references/` и `agents/` обязательны: без них агент видит
`SKILL.md`, но не открывает справочники. Навык обновляется вместе с `git pull`.

### Claude Code — для всех проектов

    mkdir -p ~/.claude/skills/onec-ops
    cp -r SKILL.md references agents ~/.claude/skills/onec-ops/

### Codex

Codex не следует симлинкам — нужна копия:

    mkdir -p ~/.codex/skills/onec-ops
    cp -r SKILL.md references agents ~/.codex/skills/onec-ops/

Перезапустите Codex.

### Обновление копий

Копии в `~/.claude/skills/` и `~/.codex/skills/` не обновляются сами.
После каждого релиза повторите `cp -r` из актуального репозитория.
Проверить, что копия актуальна:

    diff -r SKILL.md ~/.codex/skills/onec-ops/SKILL.md && \
    diff -r references ~/.codex/skills/onec-ops/references && echo "актуально"

### Проверка

В новом чате агента спросите «какие навыки ты видишь?» — в списке
должен быть `onec-ops`. Затем дайте задачу, например «выгрузи
конфигурацию базы ./base в .cf»: агент должен выбрать навык и предложить
`onec-ops --ib ./base dump-cf --to ./base.cf`.

## Codex: sandbox

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
