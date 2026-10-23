---
name: onec-ops
description: Пакетные операции с файловыми базами 1С:Предприятие 8 через CLI onec-ops. Создаёт файловую ИБ; выгружает и загружает конфигурацию и расширения (XML, .cf, .cfe); показывает, проверяет и удаляет расширения; собирает и разбирает внешние обработки и отчёты (.epf, .erf); делает бэкап и восстановление базы (.dt); работает с файловым хранилищем конфигурации (создание, подключение, обновление, пользователи); открывает Конфигуратор и клиент 1С. Используй, когда пользователь просит выгрузить или загрузить конфигурацию, сделать бэкап базы 1С, подключить базу к хранилищу, проверить или удалить расширение, собрать обработку, создать тестовую базу 1С. Не для написания кода на языке 1С и не для клиент-серверных баз.
---

# onec-ops

CLI `onec-ops` запускает толстый клиент `1cv8` в пакетном режиме.
Работает только с **файловыми** ИБ (каталог с `1Cv8.1CD`).

## Когда использовать / когда нет

Используй для: создания файловой ИБ; выгрузки и загрузки конфигурации
и расширений; бэкапа `.dt`; файлового хранилища; обработок `.epf` / `.erf`;
открытия Конфигуратора или клиента в графической сессии.

НЕ используй для: написания или правки кода 1С; клиент-серверных баз
(`Srvr=...`); серверного хранилища (`tcp://`, `http://`); управления
окнами 1С (GUI-команды только открывают окно).

## Правила безопасности

1. **Разрушающие команды** перезаписывают данные или конфигурацию ИБ:
   `create-ib --force`, `restore-dt`, `load-config`, `load-cf`,
   `delete-extension`, `repo-bind --force`. Перед запуском скажи
   пользователю, что именно будет перезаписано, и получи согласие.
2. Для рабочей базы перед разрушающей командой предложи бэкап:
   `onec-ops dump-dt --ib ... --to ...`.
3. `--yes` и `--force --yes` пропускают подтверждение — передавай их,
   только если пользователь явно попросил выполнить без вопросов.
4. Не уверен в аргументах — сначала `--dry-run`: он показывает команду
   1С и не запускает её.
5. Пароли не повторяй в ответах; неизвестные учётные данные спроси
   у пользователя, не подбирай.

## Дисплей: ЗАПРЕЩЕНО

`onec-ops` сама выбирает режим: есть `DISPLAY` — запуск напрямую;
нет — `xvfb-run -a -s "-nolisten unix"`; нет и его — ошибка.

- НЕ оборачивай `onec-ops` в `xvfb-run`.
- НЕ запускай `Xvfb` вручную.
- НЕ выставляй `DISPLAY` перед вызовом.

## Команды

У всех команд, кроме `create-ib`, обязателен `--ib PATH`.

| Задача | Команда |
| --- | --- |
| Создать файловую ИБ | `onec-ops create-ib --type file --path DIR` |
| Пересоздать ИБ (разрушает) | `onec-ops create-ib --type file --path DIR --force` |
| Конфигурация → XML | `onec-ops dump-config --ib IB --to DIR` |
| XML → конфигурация (разрушает) | `onec-ops load-config --ib IB --from DIR --update-db-cfg` |
| Конфигурация → `.cf` | `onec-ops dump-cf --ib IB --to base.cf` |
| `.cf` → конфигурация (разрушает) | `onec-ops load-cf --ib IB --from base.cf --update-db-cfg` |
| Расширение → `.cfe` | `onec-ops dump-cf --ib IB --to ext.cfe --extension Имя` |
| `.cfe` → расширение | `onec-ops load-cf --ib IB --from ext.cfe --extension Имя --update-db-cfg` |
| Список расширений | `onec-ops list-extensions --ib IB` |
| Можно ли применить расширение | `onec-ops check-extension --ib IB --extension Имя` |
| Удалить расширение (разрушает) | `onec-ops delete-extension --ib IB --extension Имя` |
| Обработка/отчёт → XML | `onec-ops dump-epf --ib IB --epf file.epf --to DIR` |
| XML → обработка/отчёт | `onec-ops load-epf --ib IB --root DIR/Имя.xml --epf file.epf` |
| Бэкап базы | `onec-ops dump-dt --ib IB --to base.dt` |
| Восстановить из бэкапа (разрушает) | `onec-ops restore-dt --ib IB --from base.dt` |
| Создать хранилище | `onec-ops repo-create --ib IB --storage DIR` |
| Подключить базу к хранилищу | `onec-ops repo-bind --ib IB --storage DIR --storage-user Имя` |
| Обновить базу из хранилища | `onec-ops repo-update --ib IB --storage DIR --storage-user Имя` |
| Добавить пользователя хранилища | `onec-ops repo-add-user --ib IB --storage DIR --storage-user Админ --user Имя --rights LockObjects` |
| Открыть Конфигуратор | `onec-ops open-designer --ib IB` |
| Открыть клиент 1С | `onec-ops open-enterprise --ib IB [--execute file.epf]` |

- `.cfe` требует `--extension Имя`; для `.cf` эта опция запрещена.
- `dump-config` / `load-config`: расширение — `--extension Имя`,
  все расширения при выгрузке — `--all-extensions`.
- Без `--update-db-cfg` загрузка не применяет конфигурацию к БД.
- `restore-dt`, `create-ib --force`, `delete-extension` спрашивают `Y`;
  без терминала нужны `--force --yes` (`restore-dt`, `create-ib`) или
  `--yes` (`delete-extension`) — см. правило безопасности 3.

Синтаксис и все параметры: [references/commands.md](references/commands.md).

## Общие параметры

Можно указывать до или после имени команды.

- `--ib PATH` — файловая ИБ с `1Cv8.1CD`.
- `--ib-user NAME` / `--ib-password PWD` — пользователь ИБ (`/N`, `/P`).
- `--platform PATH` — путь к `1cv8` (иначе `ONEC_OPS_PLATFORM` или конфиг).
- `--dry-run` — показать команду без запуска 1С.
- `--timeout SEC` (по умолчанию 600), `--log-level`, `--log-file`, `--config`.

## Пользователь ИБ

Если в ИБ есть пользователи, передай пользователя для ЛЮБОЙ команды с `--ib`,
иначе 1С сразу вернёт код 1: «Пользователь ИБ не идентифицирован».
Имя нужно и пользователю без пароля.

- Пароль лучше через окружение: `ONEC_OPS_IB_USER` / `ONEC_OPS_IB_PASSWORD`.
  Параметр CLI важнее окружения.
- `--user` / `--password` у `repo-create` и `repo-add-user` — пользователь
  ХРАНИЛИЩА; `--storage-user` / `--storage-password` — тоже хранилище.
- У GUI-команд `--user` / `--password` устарели — используй `--ib-user`.

## Результат

- Код 0 — успех. Код 1 — ошибка: после строки «1С завершилась с ненулевым
  кодом» идёт текст 1С с причиной — читай его, не гадай.
- Код 2 — ошибка аргументов (`unrecognized arguments`, нет обязательного).
- Журнал пишется в stderr. В stdout пишет только `list-extensions`
  (имена расширений по одному в строке).

## Хранилище

- Только файловое хранилище.
- `repo-create` подключает к хранилищу базу-источник автоматически;
  `--user` по умолчанию «Администратор».
- Один пользователь хранилища = одна база. Для второй базы:
  `repo-add-user` (от имени администратора через `--storage-user`),
  затем `repo-bind` под новым пользователем.
- НЕ подключай вторую базу через `repo-bind --force` под тем же
  пользователем: первая база будет отвязана.
- `--ib` у `repo-add-user` — база этого хранилища или не подключённая ни к какому.

## Расширения

- `list-extensions` — узнать имена перед `--extension`. В списке и не
  применённые к БД расширения.
- `check-extension` не меняет ИБ: код 0 — можно применить, код 1 —
  причины 1С. Запускай после загрузки расширения и после обновления
  основной конфигурации.
- `delete-extension` удаляет расширение ВМЕСТЕ С ДАННЫМИ его объектов.
- `check-extension` / `delete-extension`: ровно одно из `--extension Имя`
  или `--all-extensions`.

## GUI-команды

`open-designer`, `open-enterprise` в Linux требуют реальный `DISPLAY`
(Xvfb не используется) и недоступны в CI, Docker и sandbox Codex — тогда
попроси пользователя выполнить команду в его терминале. По умолчанию
ждут закрытия окна; `--no-wait` возвращает управление сразу.

## Типовые сценарии

Бэкап перед загрузкой конфигурации:

    onec-ops --ib ./base dump-dt --to ./backup/base.dt
    onec-ops --ib ./base load-cf --from ./new.cf --update-db-cfg

Выгрузка конфигурации и расширений в XML:

    onec-ops --ib ./base dump-config --to ./src/cf
    onec-ops --ib ./base dump-config --to ./src/cfe --all-extensions

Загрузка расширения с проверкой:

    onec-ops --ib ./base load-cf --from ./ext.cfe --extension Имя --update-db-cfg
    onec-ops --ib ./base check-extension --extension Имя

Остальные сценарии: [references/workflows.md](references/workflows.md).

## Частые ошибки

| Ошибка | Правильно |
| --- | --- |
| Тонкий клиент `1cv8c` в `--platform` | Только толстый клиент `1cv8` |
| `create-ib` в существующую ИБ без `--force` | Спросить пользователя, затем `--force` |
| Ждать ввода `Y` в CI | `--force --yes` / `--yes` по явной просьбе |
| Нет `--ib-user` на ИБ с пользователями | `--ib-user Имя` + `ONEC_OPS_IB_PASSWORD` |
| `--user` вместо `--ib-user` у пакетных команд | `--ib-user` (у `repo-*` `--user` — хранилище) |
| `--extension` для `.cf` | Только для `.cfe` |
| Обернуть в `xvfb-run` | Вызывать `onec-ops` напрямую |

Диагностика: [references/troubleshooting.md](references/troubleshooting.md).

## Ограничения

- Только файловые ИБ; клиент-серверные — не поддержаны.
- Только файловое хранилище конфигурации.
- Аутентификация ОС (`/WA`) и OpenID не поддержаны — только `/N`, `/P`.
- Файлы обновления `.cfu` не поддержаны.
- Свойства расширений (безопасный режим, активность) не меняются.
- В sandbox Codex 1С может не запуститься (изоляция `/tmp`). Не обходи
  ограничение сам — см. troubleshooting и попроси пользователя.

## Справка

- [references/commands.md](references/commands.md) — синтаксис, параметры, поведение каждой команды.
- [references/workflows.md](references/workflows.md) — типовые сценарии.
- [references/troubleshooting.md](references/troubleshooting.md) — ошибки и диагностика.
