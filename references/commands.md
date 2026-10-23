# Команды onec-ops

Справочник всех команд. Правила безопасности и выбор команды — в
[SKILL.md](../SKILL.md); сценарии — в [workflows.md](workflows.md);
ошибки — в [troubleshooting.md](troubleshooting.md).

## Оглавление

- [Общие параметры](#общие-параметры) · [Коды возврата и вывод](#коды-возврата-и-вывод) · [Пользователь ИБ](#пользователь-иб)
- ИБ: [create-ib](#create-ib) · [dump-dt](#dump-dt) · [restore-dt](#restore-dt)
- Конфигурация: [dump-config](#dump-config) · [load-config](#load-config) · [dump-cf](#dump-cf) · [load-cf](#load-cf) · [update-db](#update-db)
- Расширения: [list-extensions](#list-extensions) · [check-extension](#check-extension) · [delete-extension](#delete-extension)
- Обработки и отчёты: [dump-epf](#dump-epf) · [load-epf](#load-epf)
- Хранилище: [repo-create](#repo-create) · [repo-bind](#repo-bind) · [repo-update](#repo-update) · [repo-add-user](#repo-add-user)
- GUI: [open-designer](#open-designer) · [open-enterprise](#open-enterprise)

## Общие параметры

Указываются до или после имени команды:

```text
--ib PATH               Файловая ИБ с 1Cv8.1CD (для всех команд, кроме create-ib)
--ib-user NAME          Пользователь ИБ (/N), см. «Пользователь ИБ»
--ib-password PWD       Пароль пользователя ИБ (/P)
--platform PATH         Путь к 1cv8
--config PATH           TOML-конфиг (по умолчанию ~/.config/onec-ops/config.toml)
--log-level LEVEL       DEBUG / INFO / WARNING / ERROR (по умолчанию INFO)
--log-file PATH         Дублировать журнал в файл
--dry-run               Проверить аргументы и показать команду 1С без запуска
--timeout SEC           Таймаут запуска 1С (по умолчанию 600)
```

Путь к платформе выбирается так: `--platform` → переменная
`ONEC_OPS_PLATFORM` → ключ `platform` в TOML-конфиге →
`/opt/1cv8/x86_64/8.5.1.1343/1cv8` (Linux) или
`C:\Program Files\1cv8\8.5.1.1343\bin\1cv8.exe` (Windows).

```toml
# ~/.config/onec-ops/config.toml
platform = "/opt/1cv8/x86_64/8.3.25.1374/1cv8"
```

## Коды возврата и вывод

| Код | Значение |
| --- | --- |
| 0 | Успех |
| 1 | Ошибка проверки или 1С: текст 1С (из `/Out`) — после строки «1С завершилась с ненулевым кодом» |
| 2 | Ошибка аргументов (argparse): неизвестный или отсутствующий параметр |
| 130 | Прервано пользователем (Ctrl+C) |

Журнал пишется в stderr (и в `--log-file`). В stdout пишет только
`list-extensions`. Пароли в журнале заменены на `***`.

## Пользователь ИБ

Все команды с `--ib` принимают пользователя ИБ — общие параметры, которые
можно указывать до или после имени действия:

```text
--ib-user NAME          Пользователь ИБ (/N)
--ib-password PWD       Пароль пользователя ИБ (/P)
```

Вместо параметров можно задать переменные окружения `ONEC_OPS_IB_USER` и
`ONEC_OPS_IB_PASSWORD`; параметр CLI важнее переменной. Ключи `/N` и `/P`
вставляются сразу после `/F <ib>`, пароль маскируется в журнале. Без пароля
(или с пустым `--ib-password ""`) передаётся только `/N`; `--ib-password`
без пользователя — ошибка. Для `create-ib` параметры запрещены, переменные
окружения игнорируются.

Если в ИБ есть пользователи, без `--ib-user` 1С сразу завершается с кодом 1:
«Пользователь ИБ не идентифицирован». Это относится и к пользователю без
пароля — его имя всё равно нужно передать.

```sh
onec-ops --ib ./base --ib-user Пользователь --ib-password secret dump-cf --to ./base.cf
ONEC_OPS_IB_USER=Пользователь ONEC_OPS_IB_PASSWORD=secret onec-ops --ib ./base dump-config --to ./xml
```

## create-ib

Создаёт информационную базу 1С.

### Синтаксис

```css
onec-ops create-ib --type {file,server} [параметры]
```

### Параметры

```typescript
--type file|server      Тип ИБ (обязательный)
--path PATH             Путь к файловой ИБ (для --type file)
--force                 Удалить существующую ИБ и создать заново
--yes                   Подтвердить --force без интерактива (для CI)
--server SRV            Сервер 1С (для --type server, не поддержано — v0.3.1)
--ref NAME              Имя ИБ на сервере (для --type server, не поддержано — v0.3.1)
```

### Поведение

1. Без --force при существующей ИБ — ошибка.
2. С --force без --yes в TTY — запрос Y/n.
3. С --force без --yes в non-TTY — ошибка с подсказкой --force --yes.
4. С --force --yes — удаление каталога через shutil.rmtree и создание заново.
5. Dry-run выполняет проверки и подтверждение, но существующую ИБ не удаляет.

### Примеры

```typescript
# Новая ИБ
onec-ops create-ib --type file --path /tmp/test-ib

# Перезапись с подтверждением
onec-ops create-ib --type file --path /tmp/test-ib --force

# Перезапись без подтверждения (CI)
onec-ops create-ib --type file --path /tmp/test-ib --force --yes
```

### Что создаётся

После успешного запуска в каталоге --path появляется:

- 1Cv8.1CD — основной файл базы
- 1Cv8Log/ — каталог журнала регистрации
- служебные .cfl-файлы


## dump-config

Выгружает конфигурацию 1С в XML для хранения в Git или переноса между ИБ.

### Синтаксис

```sh
onec-ops dump-config --ib PATH --to PATH [--format {hierarchical,plain}]
                     [--extension NAME | --all-extensions]
```

### Параметры

```text
--ib PATH               Существующая файловая ИБ с 1Cv8.1CD (обязательный)
--to PATH               Каталог выгрузки (обязательный)
--format FORMAT         hierarchical (по умолчанию) или plain
--extension NAME        Выгрузить одно расширение
--all-extensions        Выгрузить все расширения
```

### Поведение

1. Проверяет наличие файла `1Cv8.1CD` в ИБ и доступность каталога для записи.
2. Создаёт каталог `--to`, включая родительские каталоги, если его нет.
3. При непустом каталоге выводит WARNING о возможной перезаписи файлов.
4. `--extension` и `--all-extensions` взаимоисключающие.
5. Передаёт 1С `/DumpConfigToFiles` и `-Format`; пути становятся абсолютными.

### Примеры

```sh
# Основная конфигурация, формат hierarchical
onec-ops dump-config --ib ./base1c --to ./xml

# Плоская структура
onec-ops dump-config --ib ./base1c --to ./xml --format plain

# Одно расширение или все расширения
onec-ops dump-config --ib ./base1c --to ./extension --extension MyExtension
onec-ops dump-config --ib ./base1c --to ./extensions --all-extensions

# Показать команду без запуска 1С
onec-ops --ib ./base1c --dry-run dump-config --to ./xml
```

### Что создаётся

В каталоге `--to` появляются XML-файлы конфигурации или расширений.
При dry-run подготавливается каталог, но XML-файлы не выгружаются.

## load-config

Загружает конфигурацию или расширения 1С из XML-выгрузки.

### Синтаксис

```sh
onec-ops load-config --ib PATH --from PATH [--extension NAME | --all-extensions]
                     [--update-db-cfg]
```

### Параметры

```text
--ib PATH               Существующая файловая ИБ с 1Cv8.1CD (обязательный)
--from PATH             Каталог XML-выгрузки (обязательный)
--extension NAME        Загрузить одно расширение
--all-extensions        Загрузить все расширения
--update-db-cfg         Обновить конфигурацию БД после загрузки
```

### Поведение

1. Проверяет наличие файла `1Cv8.1CD` в ИБ и существование каталога `--from`.
2. Для основной конфигурации проверяет `Configuration.xml` в корне `--from`.
   При `--extension NAME` или `--all-extensions` эта проверка пропускается;
   для всех расширений передавайте общий каталог выгрузки с подкаталогами расширений.
3. `--extension` и `--all-extensions` взаимоисключающие.
4. Передаёт 1С `/LoadConfigFromFiles` и `-updateConfigDumpInfo`.
5. С `--update-db-cfg` добавляет `/UpdateDBCfg` после параметров загрузки.
6. Все пути становятся абсолютными; dry-run сохраняет проверки и пропускает запуск 1С.

### Примеры

```sh
# Основная конфигурация
onec-ops load-config --ib ./base1c --from ./xml

# Загрузка с обновлением конфигурации БД
onec-ops load-config --ib ./base1c --from ./xml --update-db-cfg

# Одно расширение или все расширения
onec-ops load-config --ib ./base1c --from ./extension --extension MyExtension
onec-ops load-config --ib ./base1c --from ./extensions --all-extensions

# Показать команду без запуска 1С (XML-каталог должен пройти валидацию)
onec-ops --ib ./base1c --dry-run load-config --from ./xml --update-db-cfg
```

### Результат

Конфигурация загружается в указанную ИБ. Без `--update-db-cfg` конфигурация БД
не обновляется. Dry-run не изменяет ИБ.

Общие параметры можно указывать до или после имени действия.

## dump-cf

Выгружает конфигурацию `.cf` или расширение `.cfe` с выбором `--extension NAME`.

### Синтаксис

```sh
onec-ops dump-cf --ib PATH --to PATH [--extension NAME]
```

### Параметры

```text
--ib PATH               Существующая файловая ИБ с 1Cv8.1CD (обязательный)
--to PATH            Путь к .cf или .cfe (обязательный)
--extension NAME        Имя расширения: обязательно для .cfe, запрещено для .cf
```

### Поведение

1. Проверяет наличие файла `1Cv8.1CD` в ИБ.
2. Создаёт родительский каталог выходного файла, включая недостающих родителей.
3. Предупреждает о перезаписи существующего файла; каталог вместо файла — ошибка.
4. Передаёт 1С `/DumpCfg` и при выборе расширения `-Extension NAME`; пути абсолютные.
   `.cfe` без `--extension` и `.cf` с этой опцией — ошибки; другой суффикс — WARNING.
5. Dry-run выполняет проверки и пропускает запуск 1С. Родительский каталог создаётся, выходной файл — нет.

### Примеры

```sh
onec-ops dump-cf --ib ./base1c --to ./files/base.cf
onec-ops dump-cf --ib ./base1c --to ./files/ext.cfe --extension TestExt
onec-ops --dry-run dump-cf --ib ./base1c --to ./files/base.cf
```

## load-cf

Загружает конфигурацию `.cf` или расширение `.cfe` с выбором `--extension NAME`.

### Синтаксис

```sh
onec-ops load-cf --ib PATH --from PATH [--extension NAME] [--update-db-cfg]
```

### Параметры

```text
--ib PATH               Существующая файловая ИБ с 1Cv8.1CD (обязательный)
--from PATH          Путь к .cf или .cfe (обязательный)
--extension NAME        Имя расширения: обязательно для .cfe, запрещено для .cf
--update-db-cfg         Обновить конфигурацию БД после загрузки
```

### Поведение

1. Проверяет наличие файла `1Cv8.1CD` в ИБ.
2. Проверяет существование входного файла и размер больше нуля. Каталог не принимается.
3. С `--update-db-cfg` добавляет `/UpdateDBCfg` после параметров загрузки.
4. Передаёт 1С `/LoadCfg` и при выборе расширения `-Extension NAME`; пути абсолютные.
   `.cfe` без `--extension` и `.cf` с этой опцией — ошибки; другой суффикс — WARNING.
5. Dry-run выполняет проверки и пропускает запуск 1С.

### Примеры

```sh
onec-ops load-cf --ib ./base1c --from ./files/base.cf
onec-ops load-cf --ib ./base1c --from ./files/ext.cfe --extension TestExt
onec-ops load-cf --ib ./base1c --from ./files/base.cf --update-db-cfg
onec-ops load-cf --ib ./base1c --from ./files/ext.cfe --extension TestExt --update-db-cfg
onec-ops --dry-run load-cf --ib ./base1c --from ./files/base.cf
```

Формат `.cfu` (файл обновления конфигурации) не поддерживается.

## open-designer

Открывает интерактивный Конфигуратор.

### Синтаксис

```sh
onec-ops open-designer --ib PATH [--ib-user NAME] [--ib-password PWD] [--no-wait]
```

### Параметры

```text
--ib PATH               Файловая ИБ с 1Cv8.1CD (обязательный)
--ib-user NAME          Пользователь ИБ (общий параметр)
--ib-password PWD       Пароль пользователя ИБ (общий параметр)
--user NAME             Устарело: синоним --ib-user (WARNING в журнале)
--password PWD          Устарело: синоним --ib-password
--no-wait               Вернуть управление сразу после запуска процесса
```

### Поведение

1. Проверяет существующую файловую ИБ.
2. В Linux требует реальный DISPLAY: отсутствие или неработающий X-сервер — ошибка.
3. Проверяет X-сервер через `xdpyinfo -display`; без xdpyinfo предупреждает и продолжает.
4. При признаке sandbox (владелец `/tmp/.X11-unix` не root) возвращает понятную ошибку.
5. По умолчанию ждёт закрытия окна с таймаутом 600 с, изменяемым через `--timeout`.
6. `--no-wait` использует Popen: PID в журнале, stdout/stderr в DEVNULL.
7. Dry-run сохраняет проверку ИБ, пропускает проверки GUI и не запускает процессы.
8. В Windows запускается напрямую, без проверки DISPLAY и Linux sandbox.

Передаёт `DESIGNER /F <ib>` и необязательные `/N`, `/P`. Пароль маскируется в журнале команды.

### Примеры

```sh
onec-ops open-designer --ib ./base1c
onec-ops open-designer --ib ./base1c --no-wait
onec-ops --ib ./base1c --dry-run open-designer
```


## open-enterprise

Открывает интерактивный клиент 1С:Предприятие.

### Синтаксис

```sh
onec-ops open-enterprise --ib PATH [--ib-user NAME] [--ib-password PWD] [--execute PATH] [--c PARAM] [--no-wait]
```

### Параметры

```text
--ib PATH               Файловая ИБ с 1Cv8.1CD (обязательный)
--ib-user NAME          Пользователь ИБ (общий параметр)
--ib-password PWD       Пароль пользователя ИБ (общий параметр)
--user NAME             Устарело: синоним --ib-user (WARNING в журнале)
--password PWD          Устарело: синоним --ib-password
--execute PATH          Обработка для запуска через /Execute (абсолютный путь)
--c PARAM               Параметр запуска /C
--no-wait               Вернуть управление сразу после запуска процесса
```

### Поведение

1. Проверяет существующую файловую ИБ.
2. В Linux требует реальный DISPLAY: отсутствие или неработающий X-сервер — ошибка.
3. Проверяет X-сервер через `xdpyinfo -display`; без xdpyinfo предупреждает и продолжает.
4. При признаке sandbox (владелец `/tmp/.X11-unix` не root) возвращает понятную ошибку.
5. По умолчанию ждёт закрытия окна с таймаутом 600 с, изменяемым через `--timeout`.
6. `--no-wait` использует Popen: PID в журнале, stdout/stderr в DEVNULL.
7. Dry-run сохраняет проверку ИБ, пропускает проверки GUI и не запускает процессы.
8. В Windows запускается напрямую, без проверки DISPLAY и Linux sandbox.

Передаёт `ENTERPRISE /F <ib>` и необязательные `/N`, `/P`. Для обработки добавляет `/Execute <абсолютный путь>`, для параметра — `/C`. Пароль маскируется в журнале команды.

### Примеры

```sh
onec-ops open-enterprise --ib ./base1c
onec-ops open-enterprise --ib ./base1c --no-wait
onec-ops open-enterprise --ib ./base1c --execute ./task.epf --c "параметр"
onec-ops --ib ./base1c --dry-run open-enterprise
```

## dump-epf

Разбирает внешнюю обработку `.epf` или отчёт `.erf` в XML для версионирования.

### Синтаксис

```sh
onec-ops dump-epf --ib PATH --epf PATH --to PATH
```

### Параметры

```text
--ib PATH               Существующая файловая ИБ с 1Cv8.1CD (обязательный)
--epf PATH              Входной файл .epf или .erf (обязательный)
--to PATH               Каталог XML-выгрузки (обязательный)
```

### Поведение

1. Проверяет существование непустого входного файла и суффикс `.epf`/`.erf` без учёта регистра.
2. Проверяет доступность каталога для записи; недостающие родительские каталоги создаёт.
3. При непустом каталоге выгрузки выводит WARNING о возможной перезаписи.
4. Передаёт `/DumpExternalDataProcessorOrReportToFiles <каталог> <файл.epf|erf>`.
   Порядок аргументов: сначала каталог XML, затем файл обработки/отчёта.
5. Все пути становятся абсолютными; таймаут по умолчанию 600 секунд.
6. Dry-run сохраняет проверки, создаёт каталог, показывает команду и пропускает запуск 1С.

### Примеры

```sh
onec-ops dump-epf --ib ./base1c --epf ./ПроверкаСвязи.epf --to ./xml
onec-ops dump-epf --ib ./base1c --epf ./Отчёт.erf --to ./report-xml
onec-ops --ib ./base1c --dry-run dump-epf --epf ./ПроверкаСвязи.epf --to ./xml
```

### Что создаётся

После реального запуска 1С в `--to` появляются XML-файлы обработки или отчёта.
Dry-run XML не создаёт.

## load-epf

Собирает обработку `.epf` или отчёт `.erf` из корневого XML-файла.

### Синтаксис

```sh
onec-ops load-epf --ib PATH --root PATH --epf PATH
```

### Параметры

```text
--ib PATH               Существующая файловая ИБ с 1Cv8.1CD (обязательный)
--root PATH             Корневой XML-файл (обязательный)
--epf PATH              Выходной .epf или .erf (обязательный)
```

### Поведение

1. Проверяет существование непустого корневого `.xml` без учёта регистра суффикса.
2. Проверяет родительский каталог выходного файла на доступность записи.
3. Создаёт недостающие родительские каталоги; каталог вместо выходного файла — ошибка.
4. Передаёт `/LoadExternalDataProcessorOrReportFromFiles <root.xml> <файл.epf|erf>`.
   Порядок аргументов: сначала корневой XML, затем выходной файл.
5. Все пути становятся абсолютными; таймаут по умолчанию 600 секунд.
6. Dry-run выполняет проверки и подготовку каталогов, но выходной файл не создаёт.

### Примеры

```sh
onec-ops load-epf --ib ./base1c --root ./xml/ПроверкаСвязи.xml --epf ./build/ПроверкаСвязи.epf
onec-ops load-epf --ib ./base1c --root ./report-xml/Отчёт.xml --epf ./build/Отчёт.erf
onec-ops --ib ./base1c --dry-run load-epf --root ./xml/ПроверкаСвязи.xml --epf ./build/test.epf
```

### Результат

При успешном реальном запуске 1С создаёт файл обработки или отчёта.
Для dry-run нужен существующий XML: dry-run `dump-epf` XML-файлы не выгружает.

## dump-dt

Выгружает информационную базу в файл `.dt` для резервного копирования или переноса.

### Синтаксис

```sh
onec-ops dump-dt --ib PATH --to PATH
```

### Параметры

```text
--ib PATH               Существующая файловая ИБ с 1Cv8.1CD (обязательный)
--to PATH               Путь к выходному .dt (обязательный)
```

### Поведение

1. Проверяет наличие `1Cv8.1CD` и доступность родительского каталога для записи.
   Если каталог ещё не создан, проверяет ближайший существующий родительский каталог.
2. Создаёт недостающие родительские каталоги. Каталог вместо выходного файла — ошибка.
3. При существующем файле выводит WARNING о перезаписи.
4. Расширение, отличное от `.dt`, вызывает WARNING; регистр суффикса не важен.
5. Передаёт `DESIGNER /F <ib> /DisableStartupDialogs /DumpIB <файл.dt>`.
   Пути становятся абсолютными, таймаут по умолчанию 600 секунд.
6. Dry-run выполняет проверки и создаёт родительские каталоги, но `.dt` не создаёт.

### Примеры

```sh
onec-ops dump-dt --ib ./base1c --to ./backups/base.dt
onec-ops --ib ./base1c --dry-run dump-dt --to /tmp/backup.dt
```

### Результат

При успешном реальном запуске 1С создаёт файл бэкапа `.dt`.

## restore-dt

Восстанавливает данные и конфигурацию из `.dt` в существующую файловую ИБ.
Текущие данные и конфигурация целевой базы будут перезаписаны.

### Синтаксис

```sh
onec-ops restore-dt --ib PATH --from PATH [--force] [--yes]
```

### Параметры

```text
--ib PATH               Существующая файловая ИБ с 1Cv8.1CD (обязательный)
--from PATH             Существующий непустой .dt (обязательный)
--force                 Разрешить перезапись существующей ИБ
--yes                   Подтвердить --force без интерактива (для CI)
```

### Поведение

1. Проверяет наличие `1Cv8.1CD` и существующего непустого файла `--from`.
2. Требует расширение `.dt` без учёта регистра; другое расширение — ошибка.
3. Предупреждает о перезаписи данных и конфигурации целевой базы.
4. Без `--force` или с одним `--force` в TTY запрашивает подтверждение `Y`.
   Отказ, пустой ответ или конец ввода отменяют восстановление.
5. В non-TTY без пары `--force --yes` — ошибка с подсказкой указать оба флага.
6. С `--force --yes` выводит WARNING и продолжает без запроса.
   Один `--yes` не отменяет интерактивное подтверждение.
7. Передаёт `DESIGNER /F <ib> /DisableStartupDialogs /RestoreIB <файл.dt>`.
   Пути становятся абсолютными, таймаут по умолчанию 600 секунд.
8. Dry-run сохраняет проверки и подтверждение, показывает команду, но 1С не запускает.

### Примеры

```sh
# Восстановление с подтверждением
onec-ops restore-dt --ib ./base1c --from ./backups/base.dt
onec-ops restore-dt --ib ./base1c --from ./backups/base.dt --force

# Без интерактива (CI)
onec-ops restore-dt --ib ./base1c --from ./backups/base.dt --force --yes

# Проверка команды с уже существующим непустым .dt
onec-ops --ib ./base1c --dry-run restore-dt --from ./backups/base.dt --force --yes
```

### Результат

При успешном реальном запуске 1С восстанавливает целевую базу из бэкапа.
Dry-run `dump-dt` файл бэкапа не создаёт: для `restore-dt` подготовьте `.dt` заранее.

## repo-create

Создаёт файловое хранилище конфигурации на основе существующей файловой ИБ.

### Синтаксис

```sh
onec-ops repo-create --ib PATH --storage PATH [--user NAME] [--password PWD]
```

### Параметры

```text
--ib PATH               Существующая файловая ИБ с 1Cv8.1CD (обязательный)
--storage PATH          Каталог файлового хранилища (обязательный)
--user NAME             Администратор хранилища (по умолчанию «Администратор»)
--password PWD          Пароль администратора (опционально)
```

### Поведение

1. Проверяет ИБ и доступность родительского каталога хранилища для записи.
   Если родители ещё не созданы, проверяет ближайший существующий каталог.
2. Предупреждает (WARNING), если каталог хранилища уже существует и непустой.
   Файл вместо каталога — ошибка.
3. Создаёт недостающие каталоги, включая сам каталог хранилища.
4. Передаёт `DESIGNER /F <ib> /DisableStartupDialogs /ConfigurationRepositoryCreate <storage>`
   и непустые учётные данные через `/ConfigurationRepositoryN` и `/ConfigurationRepositoryP`.
5. Пути становятся абсолютными; пароль маскируется в журнале команды.
6. Dry-run выполняет проверки и создаёт каталог, но само хранилище не создаёт.

### Примеры

```sh
onec-ops repo-create --ib ./base1c --storage ./storage1c
onec-ops repo-create --ib ./base1c --storage ./storage1c --user admin --password secret
onec-ops --ib ./base1c --dry-run repo-create --storage ./storage1c
```

Поддерживается только файловое хранилище, без `crserver`, `tcp://` и `http://`.

## repo-bind

Подключает существующую файловую ИБ к файловому хранилищу конфигурации.

### Синтаксис

```sh
onec-ops repo-bind --ib PATH --storage PATH
                   [--storage-user NAME] [--storage-password PWD] [--force]
```

### Параметры

```text
--ib PATH               Существующая файловая ИБ с 1Cv8.1CD (обязательный)
--storage PATH          Существующий непустой каталог хранилища (обязательный)
--storage-user NAME     Пользователь хранилища (опционально)
--storage-password PWD  Пароль пользователя хранилища (опционально)
--force                 Перезаписать конфигурацию базы (-forceReplaceCfg)
```

### Поведение

1. Проверяет ИБ и существующий непустой каталог хранилища.
2. Передаёт `DESIGNER /F <ib> /DisableStartupDialogs /ConfigurationRepositoryBindCfg`
   и `/ConfigurationRepositoryF <storage>`.
3. Непустые учётные данные передаёт через `/ConfigurationRepositoryN` и
   `/ConfigurationRepositoryP`; `--force` добавляет `-forceReplaceCfg`.
4. Пути становятся абсолютными; пароль маскируется в журнале команды.
5. Dry-run сохраняет проверки и показывает команду без запуска 1С.

### Примеры

```sh
onec-ops repo-bind --ib ./other-base1c --storage ./storage1c --storage-user admin
onec-ops repo-bind --ib ./other-base1c --storage ./storage1c --storage-user admin --storage-password secret --force
onec-ops --ib ./other-base1c --dry-run repo-bind --storage ./storage1c --storage-user admin
```

Dry-run `repo-create` создаёт только каталог: для подключения нужно
хранилище, предварительно созданное реальным запуском 1С.

## repo-update

Обновляет конфигурацию существующей файловой ИБ из файлового хранилища.

### Синтаксис

```sh
onec-ops repo-update --ib PATH --storage PATH
                     [--storage-user NAME] [--storage-password PWD]
                     [--version N] [--force]
```

### Параметры

```text
--ib PATH               Существующая файловая ИБ с 1Cv8.1CD (обязательный)
--storage PATH          Существующий каталог хранилища (обязательный)
--storage-user NAME     Пользователь хранилища (опционально)
--storage-password PWD  Пароль пользователя хранилища (опционально)
--version N             Целочисленный номер версии (по умолчанию последняя)
--force                 Получить новые объекты (-force)
```

### Поведение

1. Проверяет ИБ и существование каталога хранилища.
2. Передаёт `DESIGNER /F <ib> /DisableStartupDialogs /ConfigurationRepositoryUpdateCfg`
   и `/ConfigurationRepositoryF <storage>`.
3. Непустые учётные данные передаёт через `/ConfigurationRepositoryN` и
   `/ConfigurationRepositoryP`; ненулевой `--version N` добавляет `-v N`,
   `--force` добавляет `-force`.
4. Пути становятся абсолютными; пароль маскируется в журнале команды.
5. Dry-run выполняет проверки и показывает команду без запуска 1С.

### Примеры

```sh
onec-ops repo-update --ib ./base1c --storage ./storage1c --storage-user admin
onec-ops repo-update --ib ./base1c --storage ./storage1c --version 5 --force
onec-ops --ib ./base1c --dry-run repo-update --storage ./storage1c
```

## repo-add-user

Добавляет пользователя в файловое хранилище конфигурации от имени
администратора хранилища.

### Синтаксис

```sh
onec-ops repo-add-user --ib PATH --storage PATH --user NAME --rights RIGHTS
                       [--password PWD] [--storage-user NAME]
                       [--storage-password PWD] [--restore-deleted]
```

### Параметры

```text
--ib PATH               Файловая ИБ с 1Cv8.1CD: подключённая к этому хранилищу
                        или не подключённая ни к какому (обязательный)
--storage PATH          Существующий каталог хранилища (обязательный)
--user NAME             Имя нового пользователя (обязательный)
--password PWD          Пароль нового пользователя (опционально)
--rights RIGHTS         ReadOnly | LockObjects | ManageConfigurationVersions |
                        Administration (обязательный)
--storage-user NAME     Администратор хранилища (опционально)
--storage-password PWD  Пароль администратора хранилища (опционально)
--restore-deleted       Восстановить ранее удалённого пользователя (-RestoreDeletedUser)
```

### Поведение

1. Проверяет ИБ, существование каталога хранилища и непустое имя `--user`;
   значение `--rights` проверяет argparse.
2. Передаёт `DESIGNER /F <ib> /DisableStartupDialogs /ConfigurationRepositoryF <storage>`,
   учётные данные администратора через `/ConfigurationRepositoryN` и
   `/ConfigurationRepositoryP`, затем
   `/ConfigurationRepositoryAddUser -User <имя> [-Pwd <пароль>] -Rights <права>`.
3. Без `--password` ключ `-Pwd` не передаётся: пользователь создаётся без пароля.
4. Пути становятся абсолютными; оба пароля (`/ConfigurationRepositoryP`, `-Pwd`)
   маскируются в журнале команды.
5. Dry-run выполняет проверки и показывает команду без запуска 1С.

Если `--ib` подключена к другому хранилищу, 1С завершается с кодом 1
(«Конфигурация связана с другим хранилищем»). Повторное добавление
существующего пользователя также завершается с кодом 1.

### Примеры

```sh
onec-ops repo-add-user --ib ./base1c --storage ./storage1c --storage-user Администратор \
    --user Разработчик2 --password secret --rights LockObjects
onec-ops repo-bind --ib ./base2c --storage ./storage1c \
    --storage-user Разработчик2 --storage-password secret
onec-ops --ib ./base1c --dry-run repo-add-user --storage ./storage1c --user Тестер --rights ReadOnly
```

Так к одному хранилищу подключаются несколько баз: у каждой свой пользователь.

## list-extensions

Печатает имена расширений конфигурации ИБ.

### Синтаксис

```sh
onec-ops list-extensions --ib PATH
```

### Поведение

1. Передаёт `DESIGNER /F <ib> /DisableStartupDialogs /DumpDBCfgList -AllExtensions`.
2. Из текста `/Out` берёт строки-идентификаторы 1С и печатает их в **stdout**
   по одному в строке; сообщения 1С (с пробелами и знаками) отбрасываются.
   Журнал выводится в stderr, поэтому stdout можно разбирать скриптом.
3. Нет расширений — пустой stdout и INFO «Расширений нет».
4. В список попадают все загруженные расширения, в том числе не применённые
   к БД (например, после неудачного `load-cf --update-db-cfg`). Применимость
   проверяйте через `check-extension`.
5. Dry-run показывает команду, stdout пустой.

```sh
onec-ops list-extensions --ib ./base1c
for ext in $(onec-ops --log-level WARNING list-extensions --ib ./base1c); do
    onec-ops dump-cf --ib ./base1c --to "./$ext.cfe" --extension "$ext"
done
```

## check-extension

Проверяет, можно ли применить расширение к конфигурации ИБ. ИБ не изменяется.

### Синтаксис

```sh
onec-ops check-extension --ib PATH (--extension NAME | --all-extensions)
```

### Поведение

1. Требует ровно одно: `--extension NAME` (непустое) или `--all-extensions`.
2. Передаёт `/CheckCanApplyConfigurationExtensions -Extension NAME` или
   `-AllExtensions`.
3. Код 0 — INFO «Расширение можно применить»; код 1 — ошибка с причинами
   из `/Out`, например «onec: Не найден объект Справочник.Номенклатура».

```sh
onec-ops check-extension --ib ./base1c --extension onec
onec-ops check-extension --ib ./base1c --all-extensions
```

## delete-extension

Удаляет расширение из ИБ **вместе с данными его объектов**.

### Синтаксис

```sh
onec-ops delete-extension --ib PATH (--extension NAME | --all-extensions) [--yes]
```

### Поведение

1. Требует ровно одно: `--extension NAME` (непустое) или `--all-extensions`.
2. Пишет WARNING и запрашивает подтверждение `Y` (как `restore-dt`);
   `--yes` — без вопроса. Без TTY и без `--yes` — ошибка; другой ответ —
   «Отменено пользователем».
3. Передаёт `/DeleteCfg -Extension NAME` или `-AllExtensions`.
4. Несуществующее расширение — код 1: «расширение конфигурации с указанным
   именем не найдено».
5. Dry-run запрашивает подтверждение так же, но 1С не запускает.

```sh
onec-ops delete-extension --ib ./base1c --extension onec
onec-ops delete-extension --ib ./test-ib --all-extensions --yes
```

## update-db

Применяет к базе данных конфигурацию, уже загруженную в ИБ (`/UpdateDBCfg`).
Нужна после `load-cf` / `load-config` без `--update-db-cfg`, после `repo-bind`
и `repo-update` (они меняют только конфигурацию ИБ).

### Синтаксис

```sh
onec-ops update-db --ib PATH [--extension NAME | --all-extensions]
                   [--dynamic | --no-dynamic] [--warnings-as-errors]
```

### Параметры

```text
--extension NAME        Применить только это расширение (-Extension)
--all-extensions        Применить все расширения (-AllExtensions)
--dynamic               Динамическое обновление (-Dynamic+)
--no-dynamic            Запретить динамическое обновление (-Dynamic-)
--warnings-as-errors    Предупреждения считать ошибками (-WarningsAsErrors)
```

### Поведение

1. Без выбора расширения обновляет основную конфигурацию; `--extension` и
   `--all-extensions` взаимоисключающие.
2. Без `--dynamic` / `--no-dynamic` режим выбирает платформа.
3. Пишет WARNING: объекты, удалённые из конфигурации, будут удалены из БД
   **вместе с данными**. 1С делает это без подтверждения, даже с
   `-WarningsAsErrors`; интерактивного вопроса у команды нет.
4. Код 0 и пустой ответ 1С — INFO «Изменений нет: конфигурация БД актуальна»;
   иначе — изменения 1С в журнале («Новый объект», «Объект удален») и INFO
   «Конфигурация БД обновлена».
5. Dry-run показывает команду и не запускает 1С.

```sh
onec-ops update-db --ib ./base1c
onec-ops update-db --ib ./base1c --extension onec --dynamic
onec-ops --ib ./base1c --dry-run update-db --all-extensions
```
