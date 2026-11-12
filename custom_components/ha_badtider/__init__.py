"""Integration för simtider i Piteås simhallar."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

from .coordinator import BadtiderCoordinator

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]

type BadtiderConfigEntry = ConfigEntry[BadtiderCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: BadtiderConfigEntry) -> bool:
    """Sätt upp Badtider Piteå från en config entry."""
    coordinator = BadtiderCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    @callback
    def _tick(_now) -> None:
        # Pågående/nästa pass beror på klockan, inte bara på hämtad data
        coordinator.async_update_listeners()

    entry.async_on_unload(async_track_time_change(hass, _tick, second=0))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BadtiderConfigEntry) -> bool:
    """Unloadar en config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
