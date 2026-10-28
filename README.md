# life-operating-cycles-api
The Operating rhythm cell: its own API (Railway, serverless) and its own Neon
database, described by `cell.yaml` and served by the code in `src/cellkit/`, which
this repository owns. It
reuses empire-platform for identity, authorization, executions and audit over
HTTP with the caller's token.

| | |
|---|---|
| API | Railway project `life-operating-cycles-api`, service `operating-api` (Serverless) |
| Publisher | service `operating-publisher` (Railway cron, `5 * * * *`) |
| Data | Neon project `life-operating-cycles-api`, database `operating` |
| Registry | solo-empire `repository-catalog/registries/online-systems.yaml` (`operating`) |

## API

Every resource has list, stats, get, get-by-legacy-id, create, patch and delete
(see `cellkit/app.py`). Permissions are `operating.<resource>:read|write|delete`.

| Path | Resource | Filters |
|---|---|---|
| `/v1/cycles` | cycle | `status`, `cycle_type`, `slug` |
| `/v1/cycle-tasks` | cycle-task | `cycle_id`, `task_id`, `commitment_type` |
| `/v1/cycle-goal-links` | cycle-goal-link | `cycle_id`, `goal_id`, `link_type` |
| `/v1/cycle-reviews` | cycle-review | `cycle_id`, `decision` |
| `/v1/kpis` | kpi | `status`, `metric_group`, `source_kind`, `slug` |
| `/v1/kpi-measurements` | kpi-measurement | `kpi_id`, `cycle_id`, `status` |

## Develop and operate

```bash
uv sync --frozen --all-extras          # Python 3.12 (.python-version): pgserver has no cp313 wheel yet
.venv/bin/pytest -q
.venv/bin/mypy . && uvx ruff@0.17.1 check . && uvx ruff@0.17.1 format --check .   # the same checks CI runs
NEON_API_KEY=... .venv/bin/operating-db provision
npm install && railway config apply   # service settings only; code deploys from GitHub (below)
railway scale --service operating-api asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0   # next to Neon and the platform
```

Dependencies are locked in `uv.lock`; the image installs them with `uv sync --frozen`, so
production runs the versions CI tested. Change a dependency with `uv add`/`uv lock` and commit
the lock. Product scope and measures: [PRODUCT.md](PRODUCT.md); change records: `specs/`.

Deploys (CD, since 2026-10-18): `operating-api` and `operating-publisher` are connected to this
repository's `main` with Railway's Wait for CI (`checkSuites`). A merge to `main` deploys only
after the CI and security checks pass; a failing check leaves production on the previous
deployment. Roll back by redeploying an earlier deployment in Railway. `railway up` is no
longer used.

Railway variables: `SENTRY_DSN` (error reporting; unset = off, see
`src/cellkit/_sentry.py`), `OPERATING_DB_MODE=hosted`, `OPERATING_DB_URL_API`,
`OPERATING_JWT_PUBLIC_KEY_PEM`, `OPERATING_JWT_ISSUER`, `EMPIRE_PLATFORM_URL`, and for the publisher `OPERATING_DB_URL_PUBLISHER` and `OPERATING_PUBLISHER_TOKEN`.
