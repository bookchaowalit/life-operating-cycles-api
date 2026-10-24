# SPEC-001 — L2 baseline: locked dependencies, strict types, domain rules under test

Standard: ADR-0004 — TDD + SDD (architecture-docs, `docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md`).
Big Loop Plan Wave 2 (solo-empire `repository-catalog/roadmaps/BIG-LOOP-PLAN-2026-10-21.md`).

## Document control

| Field | Value |
|---|---|
| Spec ID / version | SPEC-001 / 1.0 |
| Status | approved (2026-10-24, see Approval) |
| Repository / path | bookchaowalit/life-operating-cycles-api / `specs/001-l2-baseline/spec.md` |
| Owner (maker) | Claude Code (Wave 2 cells session) |
| Reviewer (checker) | Fresh Claude reviewer session (no maker context) |
| Approver | AI approval 2026-10-24 under the owner's process (see Approval) |
| Requirement links | Big Loop DoD L2: `PRODUCT.md`, ≥ 3 test files, Sentry, type check; L1 lockfile |
| Main-only | yes: committed straight to `main`, so the red run is local (ADR-0004 rule 2, v1.1) |
| Created / approved | 2026-10-22 / 2026-10-24 |

## 1. Problem and intent

- **Problem:** Dependencies were installed unpinned, there was no type check, the only tests were the generic contract suite, and the API stored a cycle whose `end_date` is before its `start_date`; a failed inline publish was logged but never reached Sentry.
- **Outcome:** the image installs exactly `uv.lock` (`uv sync --frozen`), CI runs Ruff, mypy
  (strict on `src/`) and a coverage gate on shared CI v1.1.1, and the cell's own rules have
  tests of their own beyond the generic contract suite.
- **Why now:** Wave 2 of the Big Loop Plan; milestone M1 is 2026-11-15.

## 2. Scope

| In scope | Out of scope (non-goals) |
|---|---|
| `uv.lock`, Dockerfile, CI caller bump, Ruff/mypy config and fixes, domain tests, `PRODUCT.md` | New endpoints or fields; database migrations; a shared cellkit package (owner decision 2026-10-21: each service owns its code) |

## 3. Behaviour — scenarios

### AC-01 — A cycle cannot end before it starts

- **Given** an owner with write permission
- **When** they create a cycle with `start_date` 2026-11-15 and `end_date` 2026-11-02
- **Then** the API answers 422 `invalid_value` naming both fields; the same day for both is accepted
- **Test:** `tests/test_cycle_validation.py::test_a_cycle_cannot_end_before_it_starts` · level: integration (API + throwaway PostgreSQL)

### AC-02 — Moving the end before the start is refused on update

- **Given** a cycle from 2026-11-02 to 2026-11-15
- **When** a patch sets `end_date` to 2026-11-01
- **Then** the API answers 422 and the stored `end_date` and version are unchanged; a patch that touches neither date still succeeds
- **Test:** `tests/test_cycle_validation.py::test_moving_the_end_before_the_start_is_refused_on_update` · level: integration (API + throwaway PostgreSQL)

### AC-03 — A task joins a cycle once, a goal links once

- **Given** a cycle with task 21 committed and goal 41 linked
- **When** the same task or goal is added again, then to another cycle
- **Then** the repeat in the same cycle is refused with 409; the other cycle accepts it
- **Test:** `tests/test_cycle_defaults.py::test_a_task_can_be_committed_to_one_cycle_only_once` · level: integration (API + throwaway PostgreSQL)

### AC-04 — A cycle has at most one review

- **Given** a cycle with a review
- **When** a second review is created for it
- **Then** the API answers 409; another cycle can still get its review
- **Test:** `tests/test_cycle_defaults.py::test_a_cycle_has_at_most_one_review` · level: integration (API + throwaway PostgreSQL)

### AC-05 — A KPI is measured once per cycle

- **Given** a KPI measured in a cycle
- **When** another measurement is created for the same KPI and cycle
- **Then** the API answers 409; other cycles and other KPIs are accepted, and a measurement must point at a KPI and cycle of the same workspace (422 otherwise)
- **Test:** `tests/test_kpi_defaults.py::test_a_kpi_is_measured_once_per_cycle` · level: integration (API + throwaway PostgreSQL)

### AC-06 — Cycles are listed by start date and grouped by declared filters

- **Given** three cycles created out of order
- **When** the owner lists them, then asks for stats by `status` or by `owner`
- **Then** they come back earliest start first (latest first with `order=desc`), stats count per status, and grouping by `owner` is refused with 422
- **Test:** `tests/test_cycle_queries.py::test_cycles_are_listed_by_start_date` · level: integration (API + throwaway PostgreSQL)

### AC-07 — A cycle or KPI with dependents cannot be deleted

- **Given** a cycle with a committed task, and a KPI with a measurement
- **When** the owner deletes the cycle or KPI
- **Then** the API answers 409 `has_dependents`; after the dependents are deleted the delete succeeds
- **Test:** `tests/test_cycle_queries.py::test_a_cycle_with_tasks_cannot_be_deleted` · level: integration (API + throwaway PostgreSQL)

### AC-08 — A failed inline publish reaches Sentry

- **Given** a resource with graph events and a publisher token, and a publisher that raises
- **When** a record is created
- **Then** the request still succeeds (the cron sweep retries) and the error is passed to Sentry `capture()`; before the fix it was only logged
- **Test:** `tests/test_contract.py::test_inline_publish_failure_is_reported` · level: integration (API + throwaway PostgreSQL)

### AC-09 — Numbers fit their columns

- **Given** an int field (PostgreSQL integer) or a real field
- **When** a client sends 2**31, or NaN / Infinity / 1e400 as raw JSON
- **Then** the API answers 422 naming the field (before: a 500 from PostgreSQL, or the value silently stored as null)
- **Test:** `tests/test_contract.py::test_numbers_fit_their_columns` · level: integration (API + throwaway PostgreSQL)

## 4. Interfaces and data

| Interface | Change | Contract |
|---|---|---|
| `POST /v1/cycles`, `PATCH /v1/cycles/{id}` | changed | `end_date` before `start_date` -> `422 {"error": "invalid_value", "fields": ["end_date", "start_date"]}` |
| `cell.yaml` | changed | new resource key `ranges: [[start_date, end_date]]` on cycle |

- **Data model / migration:** N/A — no schema change. Range rules are checked by the API on
  create and update; rows already stored are not rewritten.
- **Backward compatibility:** clients keep the same routes. A write that would store a range
  ending before it starts now gets `422 invalid_value` instead of `201/200`.

## 5. Non-functional requirements

| NFR | Target | How it is tested |
|---|---|---|
| Performance | N/A — no hot-path change beyond one comparison per declared range | — |
| Security / privacy | Same authorization, RLS and Sentry scrubbing as before | contract suite (`tests/test_contract.py`), `tests/test_sentry.py` |
| Reliability / observability | Reproducible image from `uv.lock`; failed inline publishes reach Sentry | image rehearsal before push; `test_inline_publish_failure_is_reported` |
| Accessibility / UX | N/A — API only | — |

## 6. Test plan (TDD)

- **Test levels:** integration tests against the FastAPI app with a throwaway local PostgreSQL
  (pgserver) and a fake platform; no hosted database or platform.
- **Test data:** generated in each test; no production data.
- **Coverage:** CI gate `coverage-threshold: "60"` (measured 62.30% on 2026-10-22, minus 2 points).
- **Not test-first (exceptions):** tests that pin behaviour the service already had
  (characterization tests, marked below) were written after the code by nature; tooling and
  config changes are covered by CI itself.

### Red / green log

| Scenario | Test | Red: commit / run + failure message | Green: commit / run | Refactor note |
|---|---|---|---|---|
| AC-01 | `tests/test_cycle_validation.py::test_a_cycle_cannot_end_before_it_starts` | 3ec4e77 · `.venv/bin/pytest -q tests/test_cycle_validation.py::test_a_cycle_cannot_end_before_it_starts` · `assert 201 == 422` | CI run of the pushed tip | none |
| AC-02 | `tests/test_cycle_validation.py::test_moving_the_end_before_the_start_is_refused_on_update` | 3ec4e77 · `.venv/bin/pytest -q tests/test_cycle_validation.py::test_moving_the_end_before_the_start_is_refused_on_update` · `assert 200 == 422` | CI run of the pushed tip | none |
| AC-03 | `tests/test_cycle_defaults.py::test_a_task_can_be_committed_to_one_cycle_only_once` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-04 | `tests/test_cycle_defaults.py::test_a_cycle_has_at_most_one_review` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-05 | `tests/test_kpi_defaults.py::test_a_kpi_is_measured_once_per_cycle` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-06 | `tests/test_cycle_queries.py::test_cycles_are_listed_by_start_date` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-07 | `tests/test_cycle_queries.py::test_a_cycle_with_tasks_cannot_be_deleted` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-08 | `tests/test_contract.py::test_inline_publish_failure_is_reported` | 095fe88 (origin/main) + this test only · `.venv/bin/pytest -q -k inline_publish tests/test_contract.py` · `assert captured` → `AssertionError` (nothing captured) | CI run of the pushed tip | none |
| AC-09 | `tests/test_contract.py::test_numbers_fit_their_columns` | b3b4423 · `.venv/bin/pytest -q -k numbers_fit` · `psycopg.errors.NumericValueOutOfRange: integer out of range` | CI run of the pushed tip | none |

## 7. Risks and open questions

| # | Risk or question | Impact | Owner | Resolution / date |
|---|---|---|---|---|
| 1 | Stored rows written before a range rule existed may already be inverted | a patch touching one of those dates is refused until both are fixed | owner | patches that do not touch the range still work |

## 8. Change log

| Version | Date | Change | Scenarios affected | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-10-22 | Implemented with the Wave 2 baseline | all | pending owner |

## Approval

| Gate | Role | Name / date | Decision | Evidence |
|---|---|---|---|---|
| Implemented (DoD) | Reviewer (checker) | Fresh Claude reviewer / 2026-10-22 | see Wave 2 report | CI run of the pushed tip |
| Implemented (DoD) | Approver | Owner | pending | Wave 2 report |

## Approval (2026-10-24)

| Field | Value |
|---|---|
| Checker | independent Claude reviewer subagent (`solo:solo-reviewer`, Sonnet, read-only, no maker context) |
| Approver | AI approval under the owner's process (approvals by the owner or AI with evidence; maker and checker are different agents). Recorded by Claude session oa-remainder on the owner's instruction "ทำที่เหลือให้หน่อย" (2026-10-24) |
| Verdict | **approved** |
| Tests run by the checker | .venv/bin/pytest -q: 155 passed, 19 skipped |
| Evidence | test_cycle_validation, test_cycle_defaults, test_kpi_defaults, test_cycle_queries (AC-01..07); inline publish for cycle and kpi asserts capture(); AC-09 passes. |
