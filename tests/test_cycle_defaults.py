"""Defaults and uniqueness of cycles, their tasks, goal links and reviews."""

from operating_helpers import (
    CYCLES,
    create_cycle,
    create_cycle_task,
    create_goal_link,
    create_review,
    new_cycle,
    unique_slug,
)


def test_new_cycle_defaults_to_a_planned_sprint_owned_by_the_owner(client, owner):
    response = create_cycle(client, owner)
    assert response.status_code == 201, response.text
    cycle = response.json()
    assert cycle["cycle_type"] == "sprint"
    assert cycle["status"] == "planned"
    assert cycle["owner"] == "Owner"
    assert cycle["source"] == "ai-operating-cadence"
    assert cycle["decision"] is None
    assert cycle["capacity_minutes"] is None
    assert cycle["version"] == 1


def test_slug_is_unique_across_cycles(client, owner):
    slug = unique_slug("taken")
    assert create_cycle(client, owner, slug=slug).status_code == 201
    assert create_cycle(client, owner, slug=slug).status_code == 409


def test_cycles_may_overlap_and_share_a_name(client, owner):
    dates = {"start_date": "2026-12-01", "end_date": "2026-12-14"}
    first = create_cycle(client, owner, name="Same", **dates)
    second = create_cycle(client, owner, name="Same", **dates)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text


def test_cycle_import_keeps_the_old_id(client, owner):
    imported = create_cycle(client, owner, legacy_id=77)
    assert imported.status_code == 201, imported.text
    assert imported.json()["id"] == 77
    found = client.get(f"{CYCLES}/legacy/77", headers=owner)
    assert found.status_code == 200, found.text
    assert found.json()["id"] == 77


def test_new_cycle_task_is_a_committed_task_that_needs_evidence(client, owner):
    cycle = new_cycle(client, owner)
    response = create_cycle_task(client, owner, cycle_id=cycle["id"], task_id=11)
    assert response.status_code == 201, response.text
    task = response.json()
    assert task["commitment_type"] == "committed"
    assert task["evidence_required"] is True
    assert task["estimate_minutes"] is None
    assert task["version"] == 1


def test_a_task_can_be_committed_to_one_cycle_only_once(client, owner):
    cycle = new_cycle(client, owner)
    assert (
        create_cycle_task(client, owner, cycle_id=cycle["id"], task_id=21).status_code
        == 201
    )
    again = create_cycle_task(client, owner, cycle_id=cycle["id"], task_id=21)
    assert again.status_code == 409
    other_task = create_cycle_task(client, owner, cycle_id=cycle["id"], task_id=22)
    assert other_task.status_code == 201, other_task.text


def test_the_same_task_can_join_several_cycles(client, owner):
    first, second = new_cycle(client, owner), new_cycle(client, owner)
    assert (
        create_cycle_task(client, owner, cycle_id=first["id"], task_id=31).status_code
        == 201
    )
    carried = create_cycle_task(
        client,
        owner,
        cycle_id=second["id"],
        task_id=31,
        commitment_type="carried_over",
    )
    assert carried.status_code == 201, carried.text


def test_new_goal_link_is_an_objective(client, owner):
    cycle = new_cycle(client, owner)
    response = create_goal_link(client, owner, cycle_id=cycle["id"], goal_id=3)
    assert response.status_code == 201, response.text
    assert response.json()["link_type"] == "objective"


def test_a_goal_can_be_linked_to_a_cycle_only_once(client, owner):
    cycle = new_cycle(client, owner)
    assert (
        create_goal_link(client, owner, cycle_id=cycle["id"], goal_id=41).status_code
        == 201
    )
    again = create_goal_link(
        client, owner, cycle_id=cycle["id"], goal_id=41, link_type="supporting"
    )
    assert again.status_code == 409
    other_cycle = new_cycle(client, owner)
    allowed = create_goal_link(client, owner, cycle_id=other_cycle["id"], goal_id=41)
    assert allowed.status_code == 201, allowed.text


def test_new_review_is_signed_by_the_owner(client, owner):
    cycle = new_cycle(client, owner)
    response = create_review(client, owner, cycle_id=cycle["id"])
    assert response.status_code == 201, response.text
    review = response.json()
    assert review["reviewer"] == "Owner"
    assert review["reviewed_at"] is None
    assert review["version"] == 1


def test_a_cycle_has_at_most_one_review(client, owner):
    cycle = new_cycle(client, owner)
    assert create_review(client, owner, cycle_id=cycle["id"]).status_code == 201
    second = create_review(client, owner, cycle_id=cycle["id"], decision="pause")
    assert second.status_code == 409
    other_cycle = new_cycle(client, owner)
    assert create_review(client, owner, cycle_id=other_cycle["id"]).status_code == 201
