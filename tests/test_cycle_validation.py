"""What cycles and their tasks, goal links and reviews refuse."""

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
    other_workspace,
    unique_slug,
)


def test_a_cycle_cannot_end_before_it_starts(client, owner):
    backwards = create_cycle(
        client, owner, start_date="2026-11-15", end_date="2026-11-02"
    )
    assert backwards.status_code == 422, backwards.text
    assert backwards.json()["detail"] == {
        "error": "invalid_value",
        "fields": ["end_date", "start_date"],
    }
    one_day = create_cycle(
        client, owner, start_date="2026-11-02", end_date="2026-11-02"
    )
    assert one_day.status_code == 201, one_day.text


def test_moving_the_end_before_the_start_is_refused_on_update(client, owner):
    cycle = new_cycle(client, owner, start_date="2026-11-02", end_date="2026-11-15")
    path = f"{CYCLES}/{cycle['id']}"
    refused = client.patch(path, headers=owner, json={"end_date": "2026-11-01"})
    assert refused.status_code == 422, refused.text
    stored = client.get(path, headers=owner).json()
    assert stored["end_date"] == "2026-11-15"
    assert stored["version"] == 1
    renamed = client.patch(path, headers=owner, json={"name": "Renamed"})
    assert renamed.status_code == 200, renamed.text


def test_a_cycle_needs_a_slug_name_dates_and_focus(client, owner):
    complete = {
        "slug": unique_slug("cycle"),
        "name": "Sprint",
        "start_date": "2026-11-02",
        "end_date": "2026-11-15",
        "focus": "Ship",
    }
    for missing in complete:
        body = {k: v for k, v in complete.items() if k != missing}
        refused = client.post(CYCLES, headers=owner, json=body)
        assert refused.status_code == 422, missing


def test_slug_is_limited_to_200_characters(client, owner):
    assert create_cycle(client, owner, slug="s" * 201).status_code == 422
    assert create_cycle(client, owner, slug="t" * 200).status_code == 201


def test_name_is_limited_to_500_characters(client, owner):
    assert create_cycle(client, owner, name="n" * 501).status_code == 422
    assert create_cycle(client, owner, name="n" * 500).status_code == 201


def test_cycle_type_must_be_a_known_kind(client, owner):
    assert create_cycle(client, owner, cycle_type="quarterly").status_code == 422
    assert create_cycle(client, owner, cycle_type="weekly").status_code == 201


def test_cycle_status_must_be_a_known_state(client, owner):
    assert create_cycle(client, owner, status="done").status_code == 422
    assert create_cycle(client, owner, status="in_review").status_code == 201


def test_cycle_decision_must_be_a_known_choice(client, owner):
    assert create_cycle(client, owner, decision="maybe").status_code == 422
    assert create_cycle(client, owner, decision="pause").status_code == 201


def test_capacity_cannot_be_negative(client, owner):
    assert create_cycle(client, owner, capacity_minutes=-1).status_code == 422
    assert create_cycle(client, owner, capacity_minutes=0).status_code == 201


def test_owner_is_limited_to_200_characters(client, owner):
    base = {"name": "Sprint", "start_date": "2026-11-02", "end_date": "2026-11-15"}
    for limit, expected in ((201, 422), (200, 201)):
        body = {
            **base,
            "slug": unique_slug("cycle"),
            "focus": "Ship",
            "owner": "o" * limit,
        }
        assert client.post(CYCLES, headers=owner, json=body).status_code == expected


def test_dates_must_be_real_dates(client, owner):
    assert create_cycle(client, owner, start_date="next monday").status_code == 422
    assert create_cycle(client, owner, end_date="2026-02-30").status_code == 422


def test_a_cycle_task_needs_a_cycle_and_a_task(client, owner):
    cycle = new_cycle(client, owner)
    no_task = client.post(CYCLE_TASKS, headers=owner, json={"cycle_id": cycle["id"]})
    assert no_task.status_code == 422
    no_cycle = client.post(CYCLE_TASKS, headers=owner, json={"task_id": 5})
    assert no_cycle.status_code == 422


def test_a_cycle_task_must_point_at_a_cycle_that_exists(client, owner):
    response = create_cycle_task(client, owner, cycle_id=987654321)
    assert response.status_code == 422, response.text
    assert create_cycle_task(client, owner, cycle_id=0).status_code == 422


def test_a_cycle_task_cannot_point_at_a_cycle_of_another_workspace(
    client, owner, harness, platform
):
    foreign = new_cycle(client, other_workspace(harness, platform))
    response = create_cycle_task(client, owner, cycle_id=foreign["id"])
    assert response.status_code == 422, response.text


def test_commitment_type_must_be_a_known_kind(client, owner):
    cycle = new_cycle(client, owner)
    refused = create_cycle_task(
        client, owner, cycle_id=cycle["id"], commitment_type="wish"
    )
    assert refused.status_code == 422
    accepted = create_cycle_task(
        client, owner, cycle_id=cycle["id"], commitment_type="stretch"
    )
    assert accepted.status_code == 201, accepted.text


def test_estimate_cannot_be_negative(client, owner):
    cycle = new_cycle(client, owner)
    refused = create_cycle_task(
        client, owner, cycle_id=cycle["id"], estimate_minutes=-5
    )
    assert refused.status_code == 422


def test_a_goal_link_needs_a_cycle_and_a_goal(client, owner):
    cycle = new_cycle(client, owner)
    no_goal = client.post(
        CYCLE_GOAL_LINKS, headers=owner, json={"cycle_id": cycle["id"]}
    )
    assert no_goal.status_code == 422
    missing_cycle = create_goal_link(client, owner, cycle_id=987654321)
    assert missing_cycle.status_code == 422


def test_link_type_must_be_a_known_kind(client, owner):
    cycle = new_cycle(client, owner)
    refused = create_goal_link(client, owner, cycle_id=cycle["id"], link_type="primary")
    assert refused.status_code == 422
    accepted = create_goal_link(
        client, owner, cycle_id=cycle["id"], link_type="guardrail"
    )
    assert accepted.status_code == 201, accepted.text


def test_a_review_needs_a_summary_and_a_decision(client, owner):
    cycle = new_cycle(client, owner)
    no_summary = client.post(
        CYCLE_REVIEWS,
        headers=owner,
        json={"cycle_id": cycle["id"], "decision": "continue"},
    )
    assert no_summary.status_code == 422
    no_decision = client.post(
        CYCLE_REVIEWS, headers=owner, json={"cycle_id": cycle["id"], "summary": "ok"}
    )
    assert no_decision.status_code == 422


def test_a_review_decision_must_be_a_known_choice(client, owner):
    cycle = new_cycle(client, owner)
    refused = create_review(client, owner, cycle_id=cycle["id"], decision="shrug")
    assert refused.status_code == 422


def test_a_review_must_point_at_a_cycle_that_exists(client, owner):
    assert create_review(client, owner, cycle_id=987654321).status_code == 422


def test_reviewed_at_must_be_a_timestamp(client, owner):
    cycle = new_cycle(client, owner)
    refused = create_review(client, owner, cycle_id=cycle["id"], reviewed_at="friday")
    assert refused.status_code == 422
