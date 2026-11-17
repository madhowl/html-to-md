# Участие в разработке

## Ветки

- `main` — стабильная версия.
- `develop` — интеграция.
- `feature/<имя>` — новая функциональность.
- `release/<версия>` — подготовка релиза.
- `hotfix/<имя>` — срочное исправление.

## Коммиты

Используйте Conventional Commits:

```text
feat: добавить экспорт в ODT
fix: исправить перенос таблиц
docs: обновить README
ci: добавить сборку AppImage
chore: обновить зависимости
```

## Перед PR

```bash
uv sync --frozen
uv run pytest
uv run ruff check
uv run mypy src
uv run html2doc selftest
```

PR из `feature/*` направляется в `develop`, PR из `release/*` и `hotfix/*` — в `main`. Обязательны успешные проверки CI.
