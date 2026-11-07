"""Tests for Tibber Pricing DE sensors."""

from __future__ import annotations

import aiohttp
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.tibber_pricing_de.const import DOMAIN, SENSOR_TYPES

from .conftest import FROZEN_TIME, NAME, TODAY, mock_tibber

pytestmark = pytest.mark.usefixtures("async_timeout_shim")


@pytest.fixture(autouse=True)
async def berlin_time(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Run sensor tests in Europe/Berlin at a fixed instant."""
    await hass.config.async_set_time_zone("Europe/Berlin")
    freezer.move_to(FROZEN_TIME)


def _state(hass: HomeAssistant, entity_registry: er.EntityRegistry, key: str):
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, f"{NAME} {key}")
    assert entity_id is not None, key
    return hass.states.get(entity_id)


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_sensors_from_api_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    entity_registry: er.EntityRegistry,
) -> None:
    """All sensors are created and derive their state from the hourly prices."""
    mock_tibber(aioclient_mock)
    await _setup(hass, mock_config_entry)

    # Local time is 11:30. The integration adds one hour before matching, so
    # "current" resolves to the 12:00 slot and "next hour" to 13:00.
    expected = {
        "current_price": "0.32",
        "next_hour_price": "0.33",
        "highest_price_today": "0.43",
        "lowest_price_today": "0.2",
        "highest_price_today_hour": f"{TODAY} 23:00:00",
        "lowest_price_today_hour": f"{TODAY} 00:00:00",
    }
    assert set(expected) == {d.key for d in SENSOR_TYPES}
    for key, value in expected.items():
        assert _state(hass, entity_registry, key).state == value, key

    current = _state(hass, entity_registry, "current_price")
    assert len(current.attributes["prices"]) == 24
    assert current.attributes["monthly"] == {"baseFee": 5.99}
    assert current.attributes["today"] == {"min": 0.20, "max": 0.43}
    assert current.attributes["friendly_name"] == f"{NAME} Current Price"
    assert "prices" not in _state(hass, entity_registry, "next_hour_price").attributes

    # API is called once; the remaining sensor updates are throttled.
    assert aioclient_mock.call_count == 1


async def test_sensors_unknown_when_api_unreachable(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    entity_registry: er.EntityRegistry,
) -> None:
    """Connection errors are swallowed and sensors are created without a state."""
    mock_tibber(aioclient_mock, exc=aiohttp.ClientError("boom"))
    await _setup(hass, mock_config_entry)

    for description in SENSOR_TYPES:
        assert _state(hass, entity_registry, description.key).state == STATE_UNKNOWN


async def test_sensors_unknown_on_invalid_json(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    entity_registry: er.EntityRegistry,
) -> None:
    """A non-JSON body is logged and leaves sensors without a state."""
    mock_tibber(aioclient_mock, text="not json")
    await _setup(hass, mock_config_entry)

    assert _state(hass, entity_registry, "current_price").state == STATE_UNKNOWN
