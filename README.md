# operating-cycles

The Operating rhythm cell: its own API (Railway, serverless) and its own Neon
database, described by `cell.yaml` and served by the code in `src/cellkit/`, which
this repository owns. It
reuses empire-platform for identity, authorization, executions and audit over
HTTP with the caller's token.

| | |
|---|---|
| API | Railway project `solo-operating`, service `operating-api` (Serverless) |
| Publisher | service `operating-publisher` (Railway cron, `*/15 * * * *`) |
| Data | Neon project `solo-operating`, database `operating` |
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
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/pytest -q
NEON_API_KEY=... .venv/bin/operating-db provision
npm install && railway config apply && railway up --ci --service operating-api
railway scale --service operating-api asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0   # next to Neon and the platform
```

Railway variables: `OPERATING_DB_MODE=hosted`, `OPERATING_DB_URL_API`,
`OPERATING_JWT_PUBLIC_KEY_PEM`, `OPERATING_JWT_ISSUER`, `EMPIRE_PLATFORM_URL`, and for the publisher `OPERATING_DB_URL_PUBLISHER` and `OPERATING_PUBLISHER_TOKEN`.
