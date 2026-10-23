# Типовые сценарии onec-ops

Готовые цепочки команд. Синтаксис — в [commands.md](commands.md),
ошибки — в [troubleshooting.md](troubleshooting.md).

Перед разрушающими шагами (помечены ⚠) скажи пользователю, что будет
перезаписано, и получи согласие. `--yes` — только по явной просьбе.

## Оглавление

- [Выгрузка конфигурации в git](#выгрузка-конфигурации-в-git)
- [Бэкап перед загрузкой и откат](#бэкап-перед-загрузкой-и-откат)
- [Загрузка расширения с проверкой](#загрузка-расширения-с-проверкой)
- [Выгрузка всех расширений в .cfe](#выгрузка-всех-расширений-в-cfe)
- [Вторая база в хранилище](#вторая-база-в-хранилище)
- [Сборка обработки и запуск в клиенте](#сборка-обработки-и-запуск-в-клиенте)
- [База с пользователями](#база-с-пользователями)
- [Тестовая база в CI](#тестовая-база-в-ci)

## Выгрузка конфигурации в git

Основная конфигурация и расширения — в разные каталоги:

```sh
onec-ops --ib ./base dump-config --to ./src/cf
onec-ops --ib ./base dump-config --to ./src/cfe --all-extensions
git add src && git commit -m "Выгрузка конфигурации"
```

Обратно (⚠ перезаписывает конфигурацию базы):

```sh
onec-ops --ib ./base load-config --from ./src/cf --update-db-cfg
onec-ops --ib ./base load-config --from ./src/cfe/Имя --extension Имя --update-db-cfg
```

## Бэкап перед загрузкой и откат

```sh
onec-ops --ib ./base dump-dt --to ./backup/base-$(date +%F).dt
onec-ops --ib ./base load-cf --from ./release.cf --update-db-cfg      # ⚠
```

Если что-то пошло не так (⚠ перезаписывает данные и конфигурацию):

```sh
onec-ops --ib ./base restore-dt --from ./backup/base-2026-10-23.dt
```

## Загрузка расширения с проверкой

```sh
onec-ops --ib ./base load-cf --from ./ext.cfe --extension Имя --update-db-cfg
onec-ops --ib ./base check-extension --extension Имя
```

`check-extension` с кодом 1 печатает причины 1С («Не найден объект…»).
После обновления основной конфигурации проверь все расширения:

```sh
onec-ops --ib ./base check-extension --all-extensions
```

Убрать неподходящее расширение (⚠ удаляет и данные его объектов):

```sh
onec-ops --ib ./base delete-extension --extension Имя
```

## Выгрузка всех расширений в .cfe

`list-extensions` пишет имена в stdout, журнал — в stderr:

```sh
for ext in $(onec-ops --log-level WARNING --ib ./base list-extensions); do
    onec-ops --ib ./base dump-cf --to "./cfe/$ext.cfe" --extension "$ext"
done
```

## Вторая база в хранилище

Один пользователь хранилища подключает только одну базу. Для каждой
следующей базы — свой пользователь:

```sh
onec-ops --ib ./base1 repo-create --storage ./storage                 # base1 подключена сама
onec-ops --ib ./base1 repo-add-user --storage ./storage \
    --storage-user Администратор --user Разработчик2 --rights LockObjects
onec-ops --ib ./base2 repo-bind --storage ./storage --storage-user Разработчик2
onec-ops --ib ./base2 repo-update --storage ./storage --storage-user Разработчик2
```

Если `base2` уже содержит другую конфигурацию или связана с другим
хранилищем, `repo-bind` без `--force` откажет; `--force` (⚠) заменит её
конфигурацию. Не используй `repo-bind --force` под пользователем,
который уже подключил другую базу, — та будет отвязана.

## Сборка обработки и запуск в клиенте

```sh
onec-ops --ib ./base dump-epf --epf ./Обработка.epf --to ./src/epf
# правки в ./src/epf
onec-ops --ib ./base load-epf --root ./src/epf/Обработка.xml --epf ./build/Обработка.epf
onec-ops --ib ./base open-enterprise --execute ./build/Обработка.epf
```

`open-enterprise` нужен реальный `DISPLAY`; в CI, Docker и sandbox Codex
попроси пользователя выполнить последнюю команду в его терминале.

## База с пользователями

Пароль — через окружение, чтобы он не попал в историю shell:

```sh
export ONEC_OPS_IB_USER=Администратор
export ONEC_OPS_IB_PASSWORD='***'      # значение даёт пользователь
onec-ops --ib ./base dump-cf --to ./base.cf
onec-ops --ib ./base list-extensions
```

Без пользователя 1С вернёт «Пользователь ИБ не идентифицирован» (код 1) —
даже если у пользователя нет пароля. Учётные данные не подбирай.

## Тестовая база в CI

В CI нет терминала для ответа `Y`, поэтому разрушающим командам нужны
`--yes` (это явное решение автора пайплайна):

```sh
onec-ops create-ib --type file --path ./test-ib --force --yes
onec-ops --ib ./test-ib load-cf --from ./base.cf --update-db-cfg
onec-ops --ib ./test-ib load-cf --from ./ext.cfe --extension Имя --update-db-cfg
onec-ops --ib ./test-ib check-extension --all-extensions
```

`onec-ops` сама запустит 1С через `xvfb-run`, если нет `DISPLAY` — не
оборачивай команды и не запускай Xvfb вручную.
