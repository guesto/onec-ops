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
