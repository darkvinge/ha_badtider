"""Sensorer med simtider i Piteås simhallar."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BadtiderCoordinator, Overview, Pass

if TYPE_CHECKING:
    from . import BadtiderConfigEntry

NO_SWIM = "Ingen simning"
MAX_STATE = 255


def _join(passes: list[Pass], sep: str = ", ") -> str:
    text = sep.join(p.text for p in passes) or NO_SWIM
    return text if len(text) <= MAX_STATE else text[: MAX_STATE - 1] + "…"


def _status(o: Overview) -> str:
    """Pågående pass, annars nästa pass idag, annars morgondagens första."""
    if o.ongoing:
        return "Nu: " + _join(o.ongoing, " / ")
    if o.later_today:
        return o.later_today[0].text
    if o.tomorrow_first:
        return "Imorgon: " + _join(o.tomorrow_first, " / ")
    return NO_SWIM


def _status_attrs(o: Overview) -> dict[str, Any]:
    nxt = o.upcoming[0] if o.upcoming else None
    return {
        "pagar": bool(o.ongoing),
        "pagaende": [p.as_dict() for p in o.ongoing],
        "nasta": nxt.as_dict() if nxt else None,
    }


def _next_attrs(o: Overview) -> dict[str, Any]:
    nxt = o.upcoming[0] if o.upcoming else None
    return {**(nxt.as_dict() if nxt else {}), "text": nxt.text if nxt else None}


@dataclass(frozen=True, kw_only=True)
class BadtiderSensorDescription(SensorEntityDescription):
    """Beskriver en badtidssensor."""

    value_fn: Callable[[Overview], str | datetime | None]
    attrs_fn: Callable[[Overview], dict[str, Any]]


SENSORS = (
    BadtiderSensorDescription(
        key="status",
        name="Status",
        icon="mdi:swim",
        value_fn=_status,
        attrs_fn=_status_attrs,
    ),
    BadtiderSensorDescription(
        key="idag",
        name="Idag",
        icon="mdi:calendar-today",
        value_fn=lambda o: _join(o.today),
        attrs_fn=lambda o: {"pass": [p.as_dict() for p in o.today]},
    ),
    BadtiderSensorDescription(
        key="imorgon",
        name="Imorgon första",
        icon="mdi:calendar-arrow-right",
        value_fn=lambda o: _join(o.tomorrow_first, " / "),
        attrs_fn=lambda o: {
            "forsta": [p.as_dict() for p in o.tomorrow_first],
            "pass": [p.as_dict() for p in o.tomorrow],
        },
    ),
    BadtiderSensorDescription(
        key="nasta_pass",
        name="Nästa pass",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-start",
        value_fn=lambda o: o.upcoming[0].start if o.upcoming else None,
        attrs_fn=_next_attrs,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BadtiderConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sätt upp sensorerna från en config entry."""
    coordinator = config_entry.runtime_data
    async_add_entities(BadtiderSensor(coordinator, d) for d in SENSORS)


class BadtiderSensor(CoordinatorEntity[BadtiderCoordinator], SensorEntity):
    """En sensor som räknas fram ur veckoschemana."""

    _attr_has_entity_name = True
    entity_description: BadtiderSensorDescription

    def __init__(
        self, coordinator: BadtiderCoordinator, description: BadtiderSensorDescription
    ) -> None:
        """Initiera sensorn."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "pitea_simhallar")},
            name="Badtider",
            manufacturer="Piteå kommun",
            model="Piteå simhallar",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.pitea.se/invanare/fritid-kultur/pitea-simhallar/",
        )

    @property
    def native_value(self) -> str | datetime | None:
        """Sensorns värde just nu."""
        return self.entity_description.value_fn(self.coordinator.overview())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Attribut, plus vilken period schemat gäller för varje hall."""
        attrs = self.entity_description.attrs_fn(self.coordinator.overview())
        if self.entity_description.key == "idag":
            attrs["perioder"] = {h: s.period for h, s in self.coordinator.data.items()}
        return attrs
