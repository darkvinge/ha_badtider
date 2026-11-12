"""Kalendrar med simpassen, en per hall."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, HALLS
from .coordinator import BadtiderCoordinator, Pass
from .sensor import device_info

if TYPE_CHECKING:
    from . import BadtiderConfigEntry

# Veckoschemat upprepas bara så här långt framåt och bakåt från idag, så att
# kalendern inte lovar tider långt fram som kommunen hinner ändra.
DAYS_AHEAD = 28
DAYS_BACK = 7

HALL_KEYS = {"Öjebyn": "ojebyn", "Munksund": "munksund", "Hortlax": "hortlax"}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BadtiderConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sätt upp en kalender per hall."""
    coordinator = config_entry.runtime_data
    async_add_entities(BadtiderCalendar(coordinator, hall) for hall in HALLS)


def _to_event(p: Pass) -> CalendarEvent:
    return CalendarEvent(
        start=p.start,
        end=p.end,
        summary=f"{p.type} {p.hall}",
        location=f"{p.hall} simhall",
        description=p.note,
        uid=f"{DOMAIN}_{HALL_KEYS.get(p.hall, p.hall)}_{p.start.isoformat()}",
    )


class BadtiderCalendar(CoordinatorEntity[BadtiderCoordinator], CalendarEntity):
    """Simpassen i en hall."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:swim"

    def __init__(self, coordinator: BadtiderCoordinator, hall: str) -> None:
        """Initiera kalendern."""
        super().__init__(coordinator)
        self._hall = hall
        self._attr_name = hall
        self._attr_unique_id = f"{DOMAIN}_calendar_{HALL_KEYS.get(hall, hall)}"
        self._attr_device_info = device_info()

    @property
    def event(self) -> CalendarEvent | None:
        """Pågående eller nästa pass i hallen."""
        o = self.coordinator.overview()
        for p in [*o.ongoing, *o.upcoming]:
            if p.hall == self._hall:
                return _to_event(p)
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Pass som överlappar intervallet, inom DAYS_BACK/DAYS_AHEAD från idag."""
        today = self.coordinator.now().date()
        first = max(start_date.date(), today - timedelta(days=DAYS_BACK))
        last = min(end_date.date(), today + timedelta(days=DAYS_AHEAD))
        passes = self.coordinator.passes_between(first, last)
        return [
            _to_event(p)
            for p in passes
            if p.hall == self._hall and p.start < end_date and p.end > start_date
        ]
