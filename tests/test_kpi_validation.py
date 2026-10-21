"""What KPIs and their measurements refuse."""

from operating_helpers import (
    KPI_MEASUREMENTS,
    KPIS,
    create_kpi,
    create_measurement,
    new_cycle,
    new_kpi,
    other_workspace,
    unique_slug,
)


def test_a_kpi_needs_a_slug_name_description_target_and_source(client, owner):
    complete = {
        "slug": unique_slug("kpi"),
        "name": "Tasks done",
        "description": "Finished tasks",
        "target_value": 10,
        "source_kind": "manual",
    }
    for missing in complete:
        body = {k: v for k, v in complete.items() if k != missing}
        assert client.post(KPIS, headers=owner, json=body).status_code == 422, missing


def test_source_kind_must_be_a_known_source(client, owner):
    assert create_kpi(client, owner, source_kind="spreadsheet").status_code == 422
    for source in ("cycle_tasks", "ai_telemetry", "review", "manual"):
        assert create_kpi(client, owner, source_kind=source).status_code == 201, source


def test_direction_must_be_a_known_direction(client, owner):
    assert create_kpi(client, owner, direction="sideways").status_code == 422
    assert create_kpi(client, owner, direction="decrease").status_code == 201


def test_privacy_class_must_be_a_known_class(client, owner):
    assert create_kpi(client, owner, privacy_class="secret").status_code == 422
    assert create_kpi(client, owner, privacy_class="private").status_code == 201


def test_kpi_status_must_be_a_known_state(client, owner):
    assert create_kpi(client, owner, status="deleted").status_code == 422
    assert create_kpi(client, owner, status="retired").status_code == 201


def test_kpi_text_limits(client, owner):
    assert create_kpi(client, owner, slug="s" * 201).status_code == 422
    assert create_kpi(client, owner, name="n" * 501).status_code == 422
    assert create_kpi(client, owner, unit="u" * 61).status_code == 422
    assert create_kpi(client, owner, metric_group="g" * 101).status_code == 422
    assert create_kpi(client, owner, measurement_cadence="c" * 61).status_code == 422


def test_target_value_must_be_a_number(client, owner):
    assert create_kpi(client, owner, target_value="lots").status_code == 422


def test_a_measurement_needs_a_kpi_a_cycle_a_value_and_a_target(client, owner):
    kpi, cycle = new_kpi(client, owner), new_cycle(client, owner)
    complete = {
        "kpi_id": kpi["id"],
        "cycle_id": cycle["id"],
        "value": 1,
        "target_value": 2,
    }
    for missing in complete:
        body = {k: v for k, v in complete.items() if k != missing}
        refused = client.post(KPI_MEASUREMENTS, headers=owner, json=body)
        assert refused.status_code == 422, missing


def test_a_measurement_must_point_at_a_kpi_and_cycle_that_exist(client, owner):
    kpi, cycle = new_kpi(client, owner), new_cycle(client, owner)
    no_kpi = create_measurement(client, owner, kpi_id=987654321, cycle_id=cycle["id"])
    assert no_kpi.status_code == 422, no_kpi.text
    no_cycle = create_measurement(client, owner, kpi_id=kpi["id"], cycle_id=987654321)
    assert no_cycle.status_code == 422, no_cycle.text


def test_a_measurement_cannot_point_at_records_of_another_workspace(
    client, owner, harness, platform
):
    stranger = other_workspace(harness, platform)
    foreign_kpi, foreign_cycle = new_kpi(client, stranger), new_cycle(client, stranger)
    kpi, cycle = new_kpi(client, owner), new_cycle(client, owner)
    wrong_kpi = create_measurement(
        client, owner, kpi_id=foreign_kpi["id"], cycle_id=cycle["id"]
    )
    assert wrong_kpi.status_code == 422, wrong_kpi.text
    wrong_cycle = create_measurement(
        client, owner, kpi_id=kpi["id"], cycle_id=foreign_cycle["id"]
    )
    assert wrong_cycle.status_code == 422, wrong_cycle.text


def test_measurement_status_must_be_a_known_state(client, owner):
    kpi, cycle = new_kpi(client, owner), new_cycle(client, owner)
    refused = create_measurement(
        client, owner, kpi_id=kpi["id"], cycle_id=cycle["id"], status="great"
    )
    assert refused.status_code == 422
    accepted = create_measurement(
        client, owner, kpi_id=kpi["id"], cycle_id=cycle["id"], status="achieved"
    )
    assert accepted.status_code == 201, accepted.text


def test_measured_at_must_be_a_timestamp(client, owner):
    kpi, cycle = new_kpi(client, owner), new_cycle(client, owner)
    refused = create_measurement(
        client, owner, kpi_id=kpi["id"], cycle_id=cycle["id"], measured_at="today"
    )
    assert refused.status_code == 422
