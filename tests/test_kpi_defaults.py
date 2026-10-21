"""Defaults and uniqueness of KPIs and their measurements."""

from operating_helpers import (
    KPIS,
    create_kpi,
    create_measurement,
    new_cycle,
    new_kpi,
    unique_slug,
)


def test_new_kpi_defaults_to_an_active_operating_count(client, owner):
    response = create_kpi(client, owner)
    assert response.status_code == 201, response.text
    kpi = response.json()
    assert kpi["unit"] == "count"
    assert kpi["direction"] == "increase"
    assert kpi["privacy_class"] == "internal"
    assert kpi["metric_group"] == "operating"
    assert kpi["measurement_cadence"] == "weekly"
    assert kpi["status"] == "active"
    assert kpi["version"] == 1


def test_target_value_keeps_its_decimal_value(client, owner):
    kpi = new_kpi(client, owner, target_value=82.5)
    assert kpi["target_value"] == 82.5


def test_kpi_slug_is_unique(client, owner):
    slug = unique_slug("taken")
    assert create_kpi(client, owner, slug=slug).status_code == 201
    assert create_kpi(client, owner, slug=slug).status_code == 409


def test_kpi_import_keeps_the_old_id(client, owner):
    imported = create_kpi(client, owner, legacy_id=55)
    assert imported.status_code == 201, imported.text
    assert imported.json()["id"] == 55
    found = client.get(f"{KPIS}/legacy/55", headers=owner)
    assert found.status_code == 200, found.text
    assert found.json()["id"] == 55
    assert create_kpi(client, owner, legacy_id=55).status_code == 409


def test_new_measurement_starts_with_no_data(client, owner):
    kpi, cycle = new_kpi(client, owner), new_cycle(client, owner)
    response = create_measurement(client, owner, kpi_id=kpi["id"], cycle_id=cycle["id"])
    assert response.status_code == 201, response.text
    measurement = response.json()
    assert measurement["status"] == "no_data"
    assert measurement["measured_at"] is None
    assert measurement["metadata_json"] is None
    assert measurement["version"] == 1


def test_a_kpi_is_measured_once_per_cycle(client, owner):
    kpi, cycle = new_kpi(client, owner), new_cycle(client, owner)
    ids = {"kpi_id": kpi["id"], "cycle_id": cycle["id"]}
    assert create_measurement(client, owner, **ids).status_code == 201
    assert create_measurement(client, owner, **ids, value=9).status_code == 409


def test_a_kpi_can_be_measured_in_several_cycles_and_a_cycle_by_several_kpis(
    client, owner
):
    kpi, other_kpi = new_kpi(client, owner), new_kpi(client, owner)
    first, second = new_cycle(client, owner), new_cycle(client, owner)
    for kpi_id, cycle_id in (
        (kpi["id"], first["id"]),
        (kpi["id"], second["id"]),
        (other_kpi["id"], first["id"]),
    ):
        response = create_measurement(client, owner, kpi_id=kpi_id, cycle_id=cycle_id)
        assert response.status_code == 201, response.text
