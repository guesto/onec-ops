# Участие в разработке

## Окружение

```bash
python -m venv .venv
```

```bash
.venv/bin/pip install -e ".[dev]"
```

На Windows путь к программам в окружении: `.venv\Scripts\`.

Хуки необязательны, главная проверка идёт в CI:

```bash
.venv/bin/pre-commit install
```

## Проверки

```bash
.venv/bin/ruff check onec_ops tests
```

```bash
.venv/bin/ruff format --check onec_ops tests
```

```bash
.venv/bin/pytest
```

- CI запускает их на Linux и Windows, Python 3.11–3.14.
- Порог покрытия 90%.
- Unit-тесты не запускают 1С: платформа в них заменена имитацией.
- Версия Ruff закреплена в `pyproject.toml` и `.pre-commit-config.yaml`. Меняйте её
  в обоих файлах сразу.
- Чтобы `git blame` пропускал коммит с форматированием:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

## Проверка на реальной 1С

CI не проверяет настоящую платформу, поэтому изменения команд нужно прогонять вручную.

- Работайте только на временных базах и копиях `inputs/`. Сам `inputs/` не меняется.
- Не проверяйте на рабочих базах.
- В ТЗ записывайте, на какой версии и системе проверено и что проверить не удалось.

## Новая команда

- Добавьте действие в `onec_ops/actions/` и в реестр `onec_ops/actions/__init__.py`.
- Опишите её в `SKILL.md` и `references/commands.md`. Если этого не сделать, упадёт
  `tests/test_skill.py`.
- Добавьте её в `ACTION_ARGS` в `tests/test_ib_auth.py`, если команде нужна `--ib`.

## Порядок релиза

1. ТЗ в `docs/vX.Y.Z.md` и запись в `roadmap.md`.
2. Реализация в ветке `release/vX.Y.Z` от `main`.
3. Проверка на реальной 1С и зелёный CI.
4. PR в `main`.
5. После слияния: статус в `roadmap.md`, аннотированный тег `vX.Y.Z` на merge-коммите,
   GitHub-релиз. Пуш тега запускает `.github/workflows/publish.yml`: сборка, проверка,
   что тег совпадает с `version` в `pyproject.toml`, и публикация в PyPI.

## Публикация в PyPI

Публикация идёт через Trusted Publishing, без токенов в секретах. Один раз до
первого релиза:

1. На pypi.org: Account settings → Publishing → Add a new pending publisher.
   Project name `onec-ops`, owner `guesto`, repository `onec-ops`,
   workflow `publish.yml`, environment `pypi`.
2. В GitHub: Settings → Environments → New environment `pypi`. Можно добавить
   обязательное подтверждение (Required reviewers), тогда публикация ждёт нажатия.

Проверить пакет локально:

```bash
.venv/bin/python -m build
```

```bash
.venv/bin/twine check --strict dist/*
```

```bash
python .github/scripts/check_wheel.py dist/*.whl
```

Навык (`SKILL.md`, `references/`, `agents/`) лежит в корне репозитория, в wheel он
попадает как `onec_ops/skill/` (`force-include` в `pyproject.toml`).

Номер патча идёт от последнего выпущенного релиза, а не от слота в `roadmap.md`.

## Обновление навыка

`pipx upgrade onec-ops` обновляет только пакет. Копии навыка у агентов обновляет
`onec-ops install-skill`, проверяет — `onec-ops install-skill --check`.
