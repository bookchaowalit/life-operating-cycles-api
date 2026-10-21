"""Listing, grouping and the lifecycle of cycles and what hangs off them."""

from operating_helpers import (
    CYCLE_GOAL_LINKS,
    CYCLE_REVIEWS,
    CYCLE_TASKS,
    CYCLES,
    create_cycle,
    create_cycle_task,
    create_goal_link,
    create_review,
    new_cycle,
    unique_slug,
)


def test_cycles_are_listed_by_start_date(client, owner):
    late = new_cycle(
        client, owner, name="late", start_date="2031-03-01", end_date="2031-03-14"
    )
    early = new_cycle(
        client, owner, name="early", start_date="2031-01-01", end_date="2031-01-14"
    )
    middle = new_cycle(
        client, owner, name="middle", start_date="2031-02-01", end_date="2031-02-14"
    )
    ids = [late["id"], early["id"], middle["id"]]
    listed = client.get(CYCLES, headers=owner, params={"id": ids})
    assert [c["id"] for c in listed.json()["items"]] == [
        early["id"],
        middle["id"],
        late["id"],
    ]
    reversed_ = client.get(CYCLES, headers=owner, params={"id": ids, "order": "desc"})
    assert [c["id"] for c in reversed_.json()["items"]] == [
        late["id"],
        middle["id"],
        early["id"],
    ]


def test_list_filters_by_cycle_type_and_status(client, owner):
    review = new_cycle(client, owner, cycle_type="review", status="closed")
    new_cycle(client, owner, cycle_type="planning", status="active")
    by_type = client.get(CYCLES, headers=owner, params={"cycle_type": "review"})
    assert review["id"] in [c["id"] for c in by_type.json()["items"]]
    assert {c["cycle_type"] for c in by_type.json()["items"]} == {"review"}
    by_status = client.get(CYCLES, headers=owner, params={"status": "closed"})
    assert {c["status"] for c in by_status.json()["items"]} == {"closed"}


def test_list_finds_a_cycle_by_slug(client, owner):
    slug = unique_slug("find")
    cycle = new_cycle(client, owner, slug=slug)
    new_cycle(client, owner)
    listed = client.get(CYCLES, headers=owner, params={"slug": slug})
    assert [c["id"] for c in listed.json()["items"]] == [cycle["id"]]


def test_list_refuses_a_field_that_is_not_a_filter(client, owner):
    listed = client.get(CYCLES, headers=owner, params={"focus": "Ship the cells"})
    assert listed.status_code == 422


def test_stats_count_cycles_per_status_and_type(client, owner):
    new_cycle(client, owner, status="active", cycle_type="weekly")
    new_cycle(client, owner, status="cancelled", cycle_type="weekly")
    by_status = client.get(
        f"{CYCLES}/stats", headers=owner, params={"group_by": "status"}
    )
    assert by_status.status_code == 200, by_status.text
    assert by_status.json()["groups"]["active"] >= 1
    assert by_status.json()["groups"]["cancelled"] >= 1
    by_type = client.get(
        f"{CYCLES}/stats", headers=owner, params={"group_by": "cycle_type"}
    )
    assert by_type.json()["groups"]["weekly"] >= 2


def test_stats_refuse_a_field_that_is_not_a_filter(client, owner):
    stats = client.get(f"{CYCLES}/stats", headers=owner, params={"group_by": "owner"})
    assert stats.status_code == 422


def test_closing_a_cycle_bumps_the_version_and_keeps_the_dates(client, owner):
    cycle = new_cycle(client, owner, status="active")
    path = f"{CYCLES}/{cycle['id']}"
    closed = client.patch(
        path, headers=owner, json={"status": "closed", "decision": "continue"}
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["version"] == 2
    assert closed.json()["start_date"] == cycle["start_date"]
    assert closed.json()["end_date"] == cycle["end_date"]
    unchanged = client.patch(path, headers=owner, json={"status": "closed"})
    assert unchanged.json()["version"] == 2


def test_a_required_cycle_field_cannot_be_cleared(client, owner):
    cycle = new_cycle(client, owner)
    path = f"{CYCLES}/{cycle['id']}"
    for field in ("slug", "name", "start_date", "end_date", "focus"):
        cleared = client.patch(path, headers=owner, json={field: None})
        assert cleared.status_code == 422, field


def test_tasks_are_listed_per_cycle_and_per_commitment(client, owner):
    cycle, other = new_cycle(client, owner), new_cycle(client, owner)
    committed = create_cycle_task(
        client, owner, cycle_id=cycle["id"], task_id=51
    ).json()
    stretch = create_cycle_task(
        client, owner, cycle_id=cycle["id"], task_id=52, commitment_type="stretch"
    ).json()
    create_cycle_task(client, owner, cycle_id=other["id"], task_id=51)
    in_cycle = client.get(CYCLE_TASKS, headers=owner, params={"cycle_id": cycle["id"]})
    assert {t["id"] for t in in_cycle.json()["items"]} == {
        committed["id"],
        stretch["id"],
    }
    only_stretch = client.get(
        CYCLE_TASKS,
        headers=owner,
        params={"cycle_id": cycle["id"], "commitment_type": "stretch"},
    )
    assert [t["id"] for t in only_stretch.json()["items"]] == [stretch["id"]]
    for_task = client.get(CYCLE_TASKS, headers=owner, params={"task_id": 51})
    assert len(for_task.json()["items"]) >= 2


def test_task_stats_count_commitments_and_refuse_other_fields(client, owner):
    cycle = new_cycle(client, owner)
    create_cycle_task(
        client, owner, cycle_id=cycle["id"], task_id=61, commitment_type="dropped"
    )
    stats = client.get(
        f"{CYCLE_TASKS}/stats", headers=owner, params={"group_by": "commitment_type"}
    )
    assert stats.json()["groups"]["dropped"] >= 1
    refused = client.get(
        f"{CYCLE_TASKS}/stats", headers=owner, params={"group_by": "notes"}
    )
    assert refused.status_code == 422


def test_a_cycle_task_can_be_dropped_and_changed_later(client, owner):
    cycle = new_cycle(client, owner)
    task = create_cycle_task(client, owner, cycle_id=cycle["id"], task_id=71).json()
    path = f"{CYCLE_TASKS}/{task['id']}"
    dropped = client.patch(path, headers=owner, json={"commitment_type": "dropped"})
    assert dropped.status_code == 200, dropped.text
    assert dropped.json()["version"] == 2
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404


def test_goal_links_are_listed_per_cycle_goal_and_type(client, owner):
    cycle = new_cycle(client, owner)
    objective = create_goal_link(client, owner, cycle_id=cycle["id"], goal_id=81).json()
    guard = create_goal_link(
        client, owner, cycle_id=cycle["id"], goal_id=82, link_type="guardrail"
    ).json()
    by_cycle = client.get(
        CYCLE_GOAL_LINKS, headers=owner, params={"cycle_id": cycle["id"]}
    )
    assert {g["id"] for g in by_cycle.json()["items"]} == {objective["id"], guard["id"]}
    by_type = client.get(
        CYCLE_GOAL_LINKS,
        headers=owner,
        params={"cycle_id": cycle["id"], "link_type": "guardrail"},
    )
    assert [g["id"] for g in by_type.json()["items"]] == [guard["id"]]
    by_goal = client.get(CYCLE_GOAL_LINKS, headers=owner, params={"goal_id": 81})
    assert objective["id"] in [g["id"] for g in by_goal.json()["items"]]


def test_reviews_are_listed_per_cycle_and_decision(client, owner):
    cycle = new_cycle(client, owner)
    review = create_review(
        client, owner, cycle_id=cycle["id"], decision="adjust"
    ).json()
    by_cycle = client.get(
        CYCLE_REVIEWS, headers=owner, params={"cycle_id": cycle["id"]}
    )
    assert [r["id"] for r in by_cycle.json()["items"]] == [review["id"]]
    by_decision = client.get(
        CYCLE_REVIEWS, headers=owner, params={"decision": "adjust"}
    )
    assert review["id"] in [r["id"] for r in by_decision.json()["items"]]
    stats = client.get(
        f"{CYCLE_REVIEWS}/stats", headers=owner, params={"group_by": "decision"}
    )
    assert stats.json()["groups"]["adjust"] >= 1


def test_a_review_can_be_edited_and_its_decision_changed(client, owner):
    cycle = new_cycle(client, owner)
    review = create_review(client, owner, cycle_id=cycle["id"]).json()
    path = f"{CYCLE_REVIEWS}/{review['id']}"
    edited = client.patch(
        path,
        headers=owner,
        json={"decision": "close", "reviewed_at": "2026-11-16T09:00:00+00:00"},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["decision"] == "close"
    assert edited.json()["version"] == 2


def test_a_cycle_with_tasks_cannot_be_deleted(client, owner):
    cycle = new_cycle(client, owner)
    path = f"{CYCLES}/{cycle['id']}"
    task = create_cycle_task(client, owner, cycle_id=cycle["id"], task_id=91).json()
    blocked = client.delete(path, headers=owner)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"] == {"error": "has_dependents"}
    assert (
        client.delete(f"{CYCLE_TASKS}/{task['id']}", headers=owner).status_code == 204
    )
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404


def test_an_empty_cycle_can_be_deleted(client, owner):
    cycle = create_cycle(client, owner).json()
    path = f"{CYCLES}/{cycle['id']}"
    assert client.delete(path, headers=owner).status_code == 204
    assert client.delete(path, headers=owner).status_code == 404
