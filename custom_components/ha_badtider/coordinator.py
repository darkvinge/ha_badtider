"""Gemensam hämtning av badtider och beräkning av dagens/morgondagens pass."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import BadtiderError, HallSchedule, async_fetch_schedules
from .const import DOMAIN, TIME_ZONE

_LOGGER = logging.getLogger(__name__)

# Schemat ändras sällan. Nu/nästa räknas om varje minut utan ny hämtning.
UPDATE_INTERVAL = timedelta(hours=3)


@dataclass(frozen=True)
class Pass:
    """Ett pass ett visst datum i en viss hall."""

    hall: str
    type: str
    start: datetime
    end: datetime
    note: str | None = None

    @property
    def text(self) -> str:
        """T.ex. 'Öjebyn 15:00–20:30 Simma'."""
        return f"{self.hall} {self.start:%H:%M}–{self.end:%H:%M} {self.type}"

    def as_dict(self) -> dict[str, str | None]:
        """Passet som attribut."""
        return {
            "hall": self.hall,
            "typ": self.type,
            "datum": self.start.date().isoformat(),
            "start": f"{self.start:%H:%M}",
            "slut": f"{self.end:%H:%M}",
            "notering": self.note,
        }


@dataclass(frozen=True)
class Overview:
    """Läget vid en viss tidpunkt."""

    now: datetime
    today: list[Pass]
    tomorrow: list[Pass]
    ongoing: list[Pass]
    upcoming: list[Pass]  # alla kommande pass inom en vecka, tidigast först

    @property
    def later_today(self) -> list[Pass]:
        """Pass som börjar senare idag."""
        return [p for p in self.today if p.start > self.now]

    @property
    def tomorrow_first(self) -> list[Pass]:
        """Morgondagens tidigaste pass (flera om flera hallar startar samtidigt)."""
        if not self.tomorrow:
            return []
        first = self.tomorrow[0].start
        return [p for p in self.tomorrow if p.start == first]


def passes_on(schedules: dict[str, HallSchedule], day: date, tz) -> list[Pass]:
    """Alla pass en viss dag, sorterade på starttid och hall."""
    result = []
    for hall, schedule in schedules.items():
        for s in schedule.days[day.weekday()]:
            start = datetime.combine(day, time.fromisoformat(s.start), tz)
            end = datetime.combine(day, time.fromisoformat(s.end), tz)
            result.append(Pass(hall, s.type, start, end, s.note))
    return sorted(result, key=lambda p: (p.start, p.hall))


def build_overview(schedules: dict[str, HallSchedule], now: datetime) -> Overview:
    """Räknar ut dagens, pågående och kommande pass."""
    today = now.date()
    week = [passes_on(schedules, today + timedelta(days=i), now.tzinfo) for i in range(8)]
    return Overview(
        now=now,
        today=week[0],
        tomorrow=week[1],
        ongoing=[p for p in week[0] if p.start <= now < p.end],
        upcoming=[p for day in week for p in day if p.start > now],
    )


class BadtiderCoordinator(DataUpdateCoordinator[dict[str, HallSchedule]]):
    """Hämtar veckoscheman från pitea.se."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initiera coordinatorn."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self._session = async_get_clientsession(hass)
        self._tz = dt_util.get_time_zone(TIME_ZONE)

    async def _async_update_data(self) -> dict[str, HallSchedule]:
        """Hämtar scheman. Behåller det gamla schemat om pitea.se inte svarar."""
        try:
            return await async_fetch_schedules(self._session)
        except BadtiderError as err:
            if self.data:
                _LOGGER.warning("Behåller tidigare schema, hämtning misslyckades: %s", err)
                return self.data
            raise UpdateFailed(f"Fel vid hämtning av badtider: {err}") from err

    def now(self) -> datetime:
        """Klockan i simhallarnas tidszon."""
        return dt_util.now(self._tz)

    def overview(self) -> Overview:
        """Läget just nu."""
        return build_overview(self.data, self.now())

    def passes_between(self, first: date, last: date) -> list[Pass]:
        """Alla pass från och med first till och med last."""
        result: list[Pass] = []
        day = first
        while day <= last:
            result.extend(passes_on(self.data, day, self._tz))
            day += timedelta(days=1)
        return result
