"""Tester för hämtning och tolkning av pitea.se."""

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.ha_badtider.api import (
    BadtiderConnectionError,
    async_fetch_schedules,
    parse_schedule,
)

from .conftest import mock_pages, page


def _week(hall):
    schedule = parse_schedule(page(hall))
    return schedule, [[f"{s.start}-{s.end} {s.type}" for s in day] for day in schedule.days]


def test_ojebyn():
    schedule, week = _week("Öjebyn")
    assert schedule.period == "31 augusti - 30 maj 2027"
    assert week == [
        ["06:00-08:30 Simma", "11:00-11:50 Lunchsim"],
        ["06:00-08:30 Simma", "11:00-11:50 Lunchsim", "15:00-20:30 Simma"],
        ["06:00-08:30 Simma", "11:00-11:50 Lunchsim"],
        ["06:00-08:30 Simma", "11:00-11:50 Lunchsim", "15:00-20:30 Simma"],
        ["06:00-08:30 Simma"],
        ["08:00-10:00 Simma"],
        ["08:00-10:00 Simma"],
    ]
    # Varmvattenbassängen ("Träna") ska inte komma med
    assert schedule.days[1][1].note == "11.00-11.50 Lunchsim (inga simlinor)"


def test_munksund_uses_first_schedule():
    schedule, week = _week("Munksund")
    assert schedule.period == "31 augusti - 28 maj 2027"
    assert week == [
        ["06:00-08:00 Simma", "18:00-21:00 Simma"],
        ["06:00-08:00 Simma", "11:00-11:50 Lunchsim"],
        ["06:00-08:00 Simma", "11:00-11:50 Lunchsim", "14:00-19:30 Simma"],
        ["06:00-08:00 Simma"],
        ["06:00-08:00 Simma", "11:00-11:50 Lunchsim"],
        [],
        [],
    ]


def test_hortlax():
    schedule, week = _week("Hortlax")
    assert schedule.period == "5/10 - 25/4"
    assert week == [
        ["06:00-08:00 Simma", "18:00-19:30 Simma"],
        [],
        [],
        [],
        ["06:00-07:00 Simma"],
        ["08:00-10:00 Simma"],
        ["08:00-10:00 Simma"],
    ]


def test_day_ranges_and_closed():
    html = (
        '<div id="readspeaker_button1"></div>'
        "<p><b>Måndag-onsdag</b><br>07-09 Simma<br>12-13 Leka</p>"
        "<p><b>Torsdag, fredag:</b></p><p>Stängt</p>"
        "<p><b>Lördag och söndag</b><br>9.15-10.45 Lunchsim, 11-12 Simma</p>"
        "<p>*6-8 krävs årskort</p><h3>Beskrivningar</h3><p>Måndag 1-2 Simma</p>"
    )
    days = parse_schedule(html).days
    assert [[f"{s.start}-{s.end}" for s in d] for d in days] == [
        ["07:00-09:00"],
        ["07:00-09:00"],
        ["07:00-09:00"],
        [],
        [],
        ["09:15-10:45", "11:00-12:00"],
        ["09:15-10:45", "11:00-12:00"],
    ]


async def test_fetch_skips_failing_hall(hass, aioclient_mock):
    mock_pages(aioclient_mock, fail=("Hortlax",))
    schedules = await async_fetch_schedules(async_get_clientsession(hass))
    assert list(schedules) == ["Öjebyn", "Munksund"]


async def test_fetch_all_failing(hass, aioclient_mock):
    mock_pages(aioclient_mock, fail=("Öjebyn", "Munksund", "Hortlax"))
    with pytest.raises(BadtiderConnectionError):
        await async_fetch_schedules(async_get_clientsession(hass))
