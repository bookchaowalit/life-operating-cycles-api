"""Shared helpers for the operating-rhythm domain tests."""

import uuid
from typing import Any

CYCLES = "/v1/cycles"
CYCLE_TASKS = "/v1/cycle-tasks"
CYCLE_GOAL_LINKS = "/v1/cycle-goal-links"
CYCLE_REVIEWS = "/v1/cycle-reviews"
KPIS = "/v1/kpis"
KPI_MEASUREMENTS = "/v1/kpi-measurements"


def unique_slug(prefix: str = "slug") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def create_cycle(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {
        "slug": unique_slug("cycle"),
        "name": "Sprint",
        "start_date": "2026-11-02",
        "end_date": "2026-11-15",
        "focus": "Ship the cells",
        **fields,
    }
    return client.post(CYCLES, headers=owner, json=body)


def new_cycle(client: Any, owner: dict[str, str], **fields: Any) -> dict[str, Any]:
    response = create_cycle(client, owner, **fields)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def create_cycle_task(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {"task_id": 1, **fields}
    return client.post(CYCLE_TASKS, headers=owner, json=body)


def create_goal_link(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {"goal_id": 1, **fields}
    return client.post(CYCLE_GOAL_LINKS, headers=owner, json=body)


def create_review(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {"summary": "Went fine", "decision": "continue", **fields}
    return client.post(CYCLE_REVIEWS, headers=owner, json=body)


def create_kpi(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {
        "slug": unique_slug("kpi"),
        "name": "Tasks done",
        "description": "Committed tasks finished in the cycle",
        "target_value": 10,
        "source_kind": "cycle_tasks",
        **fields,
    }
    return client.post(KPIS, headers=owner, json=body)


def new_kpi(client: Any, owner: dict[str, str], **fields: Any) -> dict[str, Any]:
    response = create_kpi(client, owner, **fields)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def create_measurement(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {"value": 4, "target_value": 10, **fields}
    return client.post(KPI_MEASUREMENTS, headers=owner, json=body)


def other_workspace(harness: Any, platform: Any) -> dict[str, str]:
    """A token of another workspace whose actor may do everything there."""
    actor = uuid.uuid4()
    platform.grants[actor] = set(harness.cell.permissions())
    return harness.token(actor, uuid.uuid4())
