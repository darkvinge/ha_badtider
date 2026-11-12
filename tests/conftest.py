"""Gemensamma fixtures för testerna."""

from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

# Importeras här så att vår custom_components laddas innan Home Assistant
# lägger till testverktygets egen custom_components-katalog i sys.path.
from custom_components.ha_badtider.const import DOMAIN, HALLS

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_FILES = {"Öjebyn": "ojebyn.html", "Munksund": "munksund.html", "Hortlax": "hortlax.html"}


def page(hall: str) -> str:
    """Sparad kopia av hallens öppettidssida på pitea.se (november 2026)."""
    return (FIXTURES / FIXTURE_FILES[hall]).read_text(encoding="utf-8")


def mock_pages(aioclient_mock, fail: tuple[str, ...] = ()) -> None:
    """Mockar alla hallars sidor, med status 500 för hallarna i fail."""
    aioclient_mock.clear_requests()
    for hall, url in HALLS.items():
        if hall in fail:
            aioclient_mock.get(url, status=500)
        else:
            aioclient_mock.get(url, text=page(hall))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Aktivera custom integrations i alla tester."""
    yield


@pytest.fixture
def config_entry():
    """En config entry för integrationen."""
    return MockConfigEntry(domain=DOMAIN, data={})
