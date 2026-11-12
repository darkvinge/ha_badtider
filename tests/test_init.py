"""Tester för uppsättning och sensorer."""

from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .conftest import mock_pages

STATUS = "sensor.badtider_status"
IDAG = "sensor.badtider_idag"
IMORGON = "sensor.badtider_imorgon_forsta"
NASTA = "sensor.badtider_nasta_pass"


async def _setup(hass, config_entry):
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def _tick(hass, freezer, to):
    freezer.move_to(to)
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def test_sensors(hass, aioclient_mock, config_entry, freezer):
    freezer.move_to("2026-11-12 09:43:00+01:00")  # torsdag
    mock_pages(aioclient_mock)
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    assert hass.states.get(STATUS).state == "Öjebyn 11:00–11:50 Lunchsim"
    assert hass.states.get(STATUS).attributes["pagar"] is False

    idag = hass.states.get(IDAG)
    assert idag.state == (
        "Munksund 06:00–08:00 Simma, Öjebyn 06:00–08:30 Simma, "
        "Öjebyn 11:00–11:50 Lunchsim, Öjebyn 15:00–20:30 Simma"
    )
    assert idag.attributes["pass"][2] == {
        "hall": "Öjebyn",
        "typ": "Lunchsim",
        "datum": "2026-11-12",
        "start": "11:00",
        "slut": "11:50",
        "notering": "11.00-11.50 Lunchsim (inga simlinor)",
    }
    assert idag.attributes["perioder"]["Hortlax"] == "5/10 - 25/4"

    assert hass.states.get(IMORGON).state == (
        "Hortlax 06:00–07:00 Simma / Munksund 06:00–08:00 Simma / Öjebyn 06:00–08:30 Simma"
    )  # fredag, alla börjar 06:00
    nasta = hass.states.get(NASTA)
    assert dt_util.parse_datetime(nasta.state) == dt_util.parse_datetime(
        "2026-11-12T11:00:00+01:00"
    )
    assert nasta.attributes["hall"] == "Öjebyn"

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_status_follows_clock(hass, aioclient_mock, config_entry, freezer):
    freezer.move_to("2026-11-12 10:59:00+01:00")
    mock_pages(aioclient_mock)
    await _setup(hass, config_entry)
    assert hass.states.get(STATUS).state == "Öjebyn 11:00–11:50 Lunchsim"

    await _tick(hass, freezer, "2026-11-12 11:00:00+01:00")
    assert hass.states.get(STATUS).state == "Nu: Öjebyn 11:00–11:50 Lunchsim"
    assert hass.states.get(STATUS).attributes["pagar"] is True

    await _tick(hass, freezer, "2026-11-12 21:00:00+01:00")
    assert hass.states.get(STATUS).state.startswith("Imorgon: Hortlax 06:00–07:00 Simma / ")


async def test_two_halls_start_at_same_time(hass, aioclient_mock, config_entry, freezer):
    freezer.move_to("2026-11-14 21:00:00+01:00")  # lördag kväll
    mock_pages(aioclient_mock)
    await _setup(hass, config_entry)

    imorgon = hass.states.get(IMORGON)
    assert imorgon.state == "Hortlax 08:00–10:00 Simma / Öjebyn 08:00–10:00 Simma"
    assert [p["hall"] for p in imorgon.attributes["forsta"]] == ["Hortlax", "Öjebyn"]
    assert hass.states.get(STATUS).state.startswith("Imorgon: Hortlax 08:00")


async def test_keeps_schedule_when_refresh_fails(hass, aioclient_mock, config_entry, freezer):
    freezer.move_to("2026-11-12 09:43:00+01:00")
    mock_pages(aioclient_mock)
    await _setup(hass, config_entry)

    mock_pages(aioclient_mock, fail=("Öjebyn", "Munksund", "Hortlax"))
    await _tick(hass, freezer, "2026-11-12 13:00:00+01:00")
    assert hass.states.get(STATUS).state == "Öjebyn 15:00–20:30 Simma"


async def test_setup_retry_when_site_fails(hass, aioclient_mock, config_entry):
    mock_pages(aioclient_mock, fail=("Öjebyn", "Munksund", "Hortlax"))
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
