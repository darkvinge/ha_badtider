"""Tester för konfigurationsflödet."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ha_badtider.const import DOMAIN

from .conftest import mock_pages

ALL = ("Öjebyn", "Munksund", "Hortlax")


async def _start_flow(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_create_entry(hass, aioclient_mock):
    mock_pages(aioclient_mock)
    result = await _start_flow(hass)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Badtider Piteå"


async def test_cannot_connect(hass, aioclient_mock):
    mock_pages(aioclient_mock, fail=ALL)
    result = await _start_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_single_instance(hass, aioclient_mock, config_entry):
    config_entry.add_to_hass(hass)
    result = await _start_flow(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
