"""Listing, grouping and the lifecycle of KPIs and their measurements."""

from operating_helpers import (
    KPI_MEASUREMENTS,
    KPIS,
    create_measurement,
    new_cycle,
    new_kpi,
    unique_slug,
)


def test_list_filters_kpis_by_status_group_and_source(client, owner):
    paused = new_kpi(
        client, owner, status="paused", metric_group="focus", source_kind="review"
    )
    new_kpi(client, owner, status="active", metric_group="operating")
    by_status = client.get(KPIS, headers=owner, params={"status": "paused"})
    assert {k["status"] for k in by_status.json()["items"]} == {"paused"}
    by_group = client.get(KPIS, headers=owner, params={"metric_group": "focus"})
    assert paused["id"] in [k["id"] for k in by_group.json()["items"]]
    by_source = client.get(KPIS, headers=owner, params={"source_kind": "review"})
    assert paused["id"] in [k["id"] for k in by_source.json()["items"]]


def test_list_finds_a_kpi_by_slug(client, owner):
    slug = unique_slug("find")
    kpi = new_kpi(client, owner, slug=slug)
    new_kpi(client, owner)
    listed = client.get(KPIS, headers=owner, params={"slug": slug})
    assert [k["id"] for k in listed.json()["items"]] == [kpi["id"]]


def test_list_refuses_a_field_that_is_not_a_filter(client, owner):
    listed = client.get(KPIS, headers=owner, params={"unit": "count"})
    assert listed.status_code == 422


def test_stats_count_kpis_per_source_kind(client, owner):
    new_kpi(client, owner, source_kind="ai_telemetry")
    new_kpi(client, owner, source_kind="ai_telemetry")
    stats = client.get(
        f"{KPIS}/stats", headers=owner, params={"group_by": "source_kind"}
    )
    assert stats.status_code == 200, stats.text
    assert stats.json()["groups"]["ai_telemetry"] >= 2


def test_stats_refuse_a_field_that_is_not_a_filter(client, owner):
    stats = client.get(f"{KPIS}/stats", headers=owner, params={"group_by": "direction"})
    assert stats.status_code == 422


def test_retiring_a_kpi_keeps_its_target(client, owner):
    kpi = new_kpi(client, owner, target_value=12)
    path = f"{KPIS}/{kpi['id']}"
    retired = client.patch(path, headers=owner, json={"status": "retired"})
    assert retired.status_code == 200, retired.text
    assert retired.json()["version"] == 2
    assert retired.json()["target_value"] == 12
    unchanged = client.patch(path, headers=owner, json={"status": "retired"})
    assert unchanged.json()["version"] == 2


def test_a_required_kpi_field_cannot_be_cleared(client, owner):
    kpi = new_kpi(client, owner)
    path = f"{KPIS}/{kpi['id']}"
    for field in ("slug", "name", "description", "target_value", "source_kind"):
        cleared = client.patch(path, headers=owner, json={field: None})
        assert cleared.status_code == 422, field


def test_measurements_are_listed_per_kpi_cycle_and_status(client, owner):
    kpi, other_kpi = new_kpi(client, owner), new_kpi(client, owner)
    first, second = new_cycle(client, owner), new_cycle(client, owner)
    on_track = create_measurement(
        client, owner, kpi_id=kpi["id"], cycle_id=first["id"], status="on_track"
    ).json()
    at_risk = create_measurement(
        client, owner, kpi_id=kpi["id"], cycle_id=second["id"], status="at_risk"
    ).json()
    create_measurement(client, owner, kpi_id=other_kpi["id"], cycle_id=first["id"])
    by_kpi = client.get(KPI_MEASUREMENTS, headers=owner, params={"kpi_id": kpi["id"]})
    assert {m["id"] for m in by_kpi.json()["items"]} == {on_track["id"], at_risk["id"]}
    by_cycle = client.get(
        KPI_MEASUREMENTS, headers=owner, params={"cycle_id": second["id"]}
    )
    assert [m["id"] for m in by_cycle.json()["items"]] == [at_risk["id"]]
    by_status = client.get(
        KPI_MEASUREMENTS,
        headers=owner,
        params={"kpi_id": kpi["id"], "status": "on_track"},
    )
    assert [m["id"] for m in by_status.json()["items"]] == [on_track["id"]]


def test_measurement_stats_count_per_status_and_refuse_other_fields(client, owner):
    kpi, cycle = new_kpi(client, owner), new_cycle(client, owner)
    create_measurement(
        client, owner, kpi_id=kpi["id"], cycle_id=cycle["id"], status="off_track"
    )
    stats = client.get(
        f"{KPI_MEASUREMENTS}/stats", headers=owner, params={"group_by": "status"}
    )
    assert stats.json()["groups"]["off_track"] >= 1
    refused = client.get(
        f"{KPI_MEASUREMENTS}/stats", headers=owner, params={"group_by": "value"}
    )
    assert refused.status_code == 422


def test_updating_a_measurement_records_the_new_value(client, owner):
    kpi, cycle = new_kpi(client, owner), new_cycle(client, owner)
    measurement = create_measurement(
        client, owner, kpi_id=kpi["id"], cycle_id=cycle["id"], value=3
    ).json()
    path = f"{KPI_MEASUREMENTS}/{measurement['id']}"
    updated = client.patch(
        path,
        headers=owner,
        json={
            "value": 10,
            "status": "achieved",
            "measured_at": "2026-11-15T18:00:00+00:00",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["value"] == 10
    assert updated.json()["version"] == 2
    unchanged = client.patch(path, headers=owner, json={"value": 10})
    assert unchanged.json()["version"] == 2


def test_a_kpi_with_measurements_cannot_be_deleted(client, owner):
    kpi, cycle = new_kpi(client, owner), new_cycle(client, owner)
    measurement = create_measurement(
        client, owner, kpi_id=kpi["id"], cycle_id=cycle["id"]
    ).json()
    blocked = client.delete(f"{KPIS}/{kpi['id']}", headers=owner)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"] == {"error": "has_dependents"}
    path = f"{KPI_MEASUREMENTS}/{measurement['id']}"
    assert client.delete(path, headers=owner).status_code == 204
    assert client.delete(f"{KPIS}/{kpi['id']}", headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404
