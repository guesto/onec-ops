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
.venv/bin/ruff check scripts tests
```

```bash
.venv/bin/ruff format --check scripts tests
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

- Добавьте действие в `scripts/actions/` и в реестр `scripts/actions/__init__.py`.
- Опишите её в `SKILL.md` и `references/commands.md`. Если этого не сделать, упадёт
  `tests/test_skill.py`.
- Добавьте её в `ACTION_ARGS` в `tests/test_ib_auth.py`, если команде нужна `--ib`.

## Порядок релиза

1. ТЗ в `docs/vX.Y.Z.md` и запись в `roadmap.md`.
2. Реализация в ветке `release/vX.Y.Z` от `main`.
3. Проверка на реальной 1С и зелёный CI.
4. PR в `main`.
5. После слияния: статус в `roadmap.md`, аннотированный тег на merge-коммите, GitHub-релиз.

Номер патча идёт от последнего выпущенного релиза, а не от слота в `roadmap.md`.

## Обновление навыка

`pipx` обновляет только CLI. После релиза скопируйте `SKILL.md`, `references` и `agents`
в `~/.claude/skills/onec-ops` и `~/.codex/skills/onec-ops`.
