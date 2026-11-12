"""Tester för kalendrarna."""

import pytest
from homeassistant.util import dt as dt_util

from .conftest import mock_pages

OJEBYN = "calendar.badtider_ojebyn"
MUNKSUND = "calendar.badtider_munksund"
HORTLAX = "calendar.badtider_hortlax"


@pytest.fixture(autouse=True)
async def stockholm(hass):
    """Kalenderns tidsattribut visas i HA:s tidszon, som hos användaren."""
    await hass.config.async_set_time_zone("Europe/Stockholm")


async def _setup(hass, config_entry):
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def _events(hass, entity_id, start, end):
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": start, "end_date_time": end},
        blocking=True,
        return_response=True,
    )
    return response[entity_id]["events"]


async def test_calendar_state(hass, aioclient_mock, config_entry, freezer):
    freezer.move_to("2026-11-12 09:43:00+01:00")  # torsdag
    mock_pages(aioclient_mock)
    await _setup(hass, config_entry)

    ojebyn = hass.states.get(OJEBYN)
    assert ojebyn.state == "off"
    assert ojebyn.attributes["message"] == "Lunchsim Öjebyn"
    assert ojebyn.attributes["location"] == "Öjebyn simhall"
    assert ojebyn.attributes["description"] == "11.00-11.50 Lunchsim (inga simlinor)"
    assert ojebyn.attributes["start_time"] == "2026-11-12 11:00:00"

    # Munksund har inget mer idag, nästa är fredag morgon
    assert hass.states.get(MUNKSUND).attributes["start_time"] == "2026-11-13 06:00:00"


async def test_calendar_turns_on_during_pass(hass, aioclient_mock, config_entry, freezer):
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    freezer.move_to("2026-11-12 10:59:00+01:00")
    mock_pages(aioclient_mock)
    await _setup(hass, config_entry)
    assert hass.states.get(OJEBYN).state == "off"

    freezer.move_to("2026-11-12 11:00:00+01:00")
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(OJEBYN).state == "on"


async def test_get_events(hass, aioclient_mock, config_entry, freezer):
    freezer.move_to("2026-11-12 09:43:00+01:00")
    mock_pages(aioclient_mock)
    await _setup(hass, config_entry)

    events = await _events(hass, HORTLAX, "2026-11-12T00:00:00+01:00", "2026-11-17T00:00:00+01:00")
    assert [(e["start"], e["summary"]) for e in events] == [
        ("2026-11-13T06:00:00+01:00", "Simma Hortlax"),
        ("2026-11-14T08:00:00+01:00", "Simma Hortlax"),
        ("2026-11-15T08:00:00+01:00", "Simma Hortlax"),
        ("2026-11-16T06:00:00+01:00", "Simma Hortlax"),
        ("2026-11-16T18:00:00+01:00", "Simma Hortlax"),
    ]


async def test_get_events_limited_range(hass, aioclient_mock, config_entry, freezer):
    freezer.move_to("2026-11-12 09:43:00+01:00")
    mock_pages(aioclient_mock)
    await _setup(hass, config_entry)

    events = await _events(hass, OJEBYN, "2026-10-01T00:00:00+02:00", "2027-03-01T00:00:00+01:00")
    starts = [dt_util.parse_datetime(e["start"]) for e in events]
    assert min(starts).date().isoformat() == "2026-11-05"  # en vecka bakåt
    assert max(starts).date().isoformat() == "2026-12-10"  # fyra veckor framåt
