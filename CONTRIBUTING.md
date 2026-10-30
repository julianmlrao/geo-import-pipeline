# Mitwirken

- Issues und Pull Requests sind willkommen. Code und Commit-Nachrichten auf Englisch, Dokumentation auf Deutsch.
- Vor dem Pull Request: `uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest -q` (Datenbanktests mit `GEO_IMPORT_TEST_DSN`, siehe README).
- Neue Quellen gehören als YAML in `config/sources/` (siehe `docs/NEUE_QUELLE.md`), neue Adapter nach `src/geo_import/adapters/` mit Test.
- Beiträge stehen unter Apache-2.0.
