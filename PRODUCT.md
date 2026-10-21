# Product

<!-- impeccable:product-schema 1 -->

## Platform

api

## Users

- The Solo Empire owner, through the cell's own MCP server (`operating-mcp`) and the hosted tool
  hub (`platform-mcp-remote-worker`, which lists this service's host in its allow-list).
- Local tooling that reads the cell through `EMPIRE_OPERATING_API`: `ops-toolkit`
  (`cell_store.py`) and `mcp-aggregator` (`cell-store.ts`), as recorded in the online-systems
  registry.
- Other cells that point at a cycle through plain ids: tasks (`task_id`) and goals (`goal_id`)
  live in their own services and are not foreign keys.
- Automations with an `empire-platform` token (for example `owner-mcp`), within the permissions
  `operating.<resource>:read|write|delete` for `cycle`, `cycle-task`, `cycle-goal-link`,
  `cycle-review`, `kpi` and `kpi-measurement`.
- A web page that shows cycles or KPIs: [ต้องยืนยัน].

## Product Purpose

The operating rhythm of the owner's work: cycles (sprint, weekly, planning, review) with the tasks
committed to each, the goals each cycle serves, one review per cycle, and the operating KPIs with
one measurement per KPI per cycle.

Success: every cycle that ran has its dates, its committed tasks and a review with a decision, and
every KPI is measured against its target once per cycle.

## Positioning

One capability, one service: its own API (Railway, serverless) with a publisher cron, its own
database (Neon) with row-level security per workspace, and authorization, executions and audit
through `empire-platform`. It is workspace-scoped, so the same service can serve other tenants
without code changes.

## Operating Context

- Production: `https://operating-api-production.up.railway.app` (`/health`), deployed by merging
  to `main` after CI. The `operating-publisher` cron (every 15 minutes) delivers graph events for
  cycles and KPIs.
- 19 rows were imported from the retired SQLite tables keeping their ids (`legacy_id`).
- Monitored by `platform-uptime-worker` (target `operating-api`); errors go to Sentry without
  personal data.

## Capabilities and Constraints

- `/v1/cycles` (filters `status`, `cycle_type`, `slug`; listed by `start_date`), `/v1/cycle-tasks`
  (`cycle_id`, `task_id`, `commitment_type`), `/v1/cycle-goal-links` (`cycle_id`, `goal_id`,
  `link_type`), `/v1/cycle-reviews` (`cycle_id`, `decision`), `/v1/kpis` (`status`,
  `metric_group`, `source_kind`, `slug`) and `/v1/kpi-measurements` (`kpi_id`, `cycle_id`,
  `status`). Each has list, stats, get, get-by-legacy-id, create (with `Idempotency-Key`), patch
  (with `expected_version`) and delete.
- Cycle rules: `slug` is unique (at most 200 characters), `name` at most 500; `slug`, `name`,
  `start_date`, `end_date` and `focus` are required; `end_date` cannot be before `start_date`
  (422 `invalid_value` naming both fields, on create and on patch; the same day is allowed);
  `capacity_minutes` cannot be negative; `cycle_type` (sprint, weekly, planning, review),
  `status` (planned, active, in_review, closed, cancelled) and `decision` are fixed enums;
  defaults are a planned sprint owned by `Owner`.
- Task rules: a task joins a cycle once (409 on repeat) but may join several cycles; the cycle must
  exist in the same workspace (422); `commitment_type` is committed, stretch, carried_over or
  dropped; `estimate_minutes` cannot be negative.
- Goal link rules: a goal links to a cycle once; `link_type` is objective, supporting or guardrail.
- Review rules: a cycle has at most one review (409 on a second); `summary` and `decision` are
  required.
- KPI rules: `slug` is unique; `description`, `target_value` and `source_kind` (cycle_tasks,
  ai_telemetry, review, manual) are required; a KPI has one measurement per cycle (409 on repeat);
  a measurement starts as `no_data`.
- A cycle with tasks, links, a review or measurements, and a KPI with measurements, cannot be
  deleted until they are removed (409 `has_dependents`). Unknown fields are refused (422); an
  unchanged patch keeps the version.
- Out of scope: computing KPI values or deciding a status (callers send both), checking that
  `task_id` or `goal_id` exist in their own services, and planning or scheduling of cycles.

## Measures

Proposed, nothing collects them yet:

- Closed cycles that have a review (target: all).
- KPIs with a measurement for the latest closed cycle.
- 5xx rate and p95 latency on `/v1/cycles` (Sentry and uptime worker).
