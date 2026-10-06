# Команды onec-ops

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
--server SRV            Сервер 1С (для --type server, v0.1.1)
--ref NAME              Имя ИБ на сервере (для --type server, v0.1.1)
```

### Поведение

1. Без --force при существующей ИБ — ошибка.
2. С --force без --yes в TTY — запрос Y/n.
3. С --force без --yes в non-TTY — ошибка с подсказкой --force --yes.
4. С --force --yes — удаление каталога через shutil.rmtree и создание заново.

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
2. Проверяет файл `Configuration.xml`; при `--extension NAME` проверка пропускается.
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
