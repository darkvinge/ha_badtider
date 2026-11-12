"""Konfigurationsflöde för Badtider Piteå."""

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BadtiderConnectionError, async_fetch_schedules
from .const import DOMAIN


class BadtiderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hanterar konfigurationsflödet för Badtider Piteå."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Bekräfta och kontrollera att pitea.se svarar."""
        errors = {}

        if user_input is not None:
            try:
                await async_fetch_schedules(async_get_clientsession(self.hass))
            except BadtiderConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Badtider Piteå", data={})

        return self.async_show_form(step_id="user", errors=errors)
