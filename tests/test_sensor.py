"""Tests for Tibber Pricing DE sensors."""

from __future__ import annotations

from datetime import timedelta

import aiohttp
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.sensor import (
    ATTR_STATE_CLASS,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.tibber_pricing_de.const import DOMAIN, UPDATE_INTERVAL
from custom_components.tibber_pricing_de.sensor import SENSOR_TYPES

from .conftest import FROZEN_TIME, TITLE, mock_api_data, mock_tibber

PREFIX = "sensor.tibber_pricing_de_10115"


@pytest.fixture(autouse=True)
async def berlin_time(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Run sensor tests in Europe/Berlin at a fixed instant."""
    await hass.config.async_set_time_zone("Europe/Berlin")
    freezer.move_to(FROZEN_TIME)


def _state(hass: HomeAssistant, key: str) -> State:
    state = hass.states.get(f"{PREFIX}_{key}")
    assert state is not None, key
    return state


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _move_to(hass: HomeAssistant, freezer: FrozenDateTimeFactory, when: str) -> None:
    freezer.move_to(when)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_sensors_from_api_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    entity_registry: er.EntityRegistry,
) -> None:
    """All sensors derive their state from the hourly prices at 11:30 local time."""
    mock_tibber(aioclient_mock)
    await _setup(hass, mock_config_entry)

    expected = {
        "current_price": "0.31",
        "next_hour_price": "0.32",
        "highest_price_today": "0.43",
        "lowest_price_today": "0.2",
        # 23:00 and 00:00 Europe/Berlin
        "highest_price_today_hour": "2026-11-07T22:00:00+00:00",
        "lowest_price_today_hour": "2026-11-06T23:00:00+00:00",
    }
    assert set(expected) == {d.key for d in SENSOR_TYPES}
    for key, value in expected.items():
        assert _state(hass, key).state == value, key
        entry = entity_registry.async_get(f"{PREFIX}_{key}")
        assert entry is not None
        assert entry.unique_id == f"{mock_config_entry.entry_id}_{key}"

    assert aioclient_mock.call_count == 1


async def test_sensor_metadata(hass: HomeAssistant, mock_config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    """Price sensors carry a unit; hour sensors are timestamps without a state class."""
    mock_tibber(aioclient_mock)
    await _setup(hass, mock_config_entry)

    current = _state(hass, "current_price")
    assert current.attributes[ATTR_FRIENDLY_NAME] == f"{TITLE} Current price"
    assert current.attributes[ATTR_UNIT_OF_MEASUREMENT] == "EUR/kWh"
    assert current.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert ATTR_DEVICE_CLASS not in current.attributes

    for key in ("next_hour_price", "highest_price_today", "lowest_price_today"):
        state = _state(hass, key)
        assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "EUR/kWh", key
        assert ATTR_STATE_CLASS not in state.attributes, key

    for key in ("highest_price_today_hour", "lowest_price_today_hour"):
        state = _state(hass, key)
        assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.TIMESTAMP, key
        assert ATTR_STATE_CLASS not in state.attributes, key
        assert ATTR_UNIT_OF_MEASUREMENT not in state.attributes, key


async def test_sensor_attributes(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    """Each sensor exposes the components of its own slot; current price adds the overview."""
    mock_tibber(aioclient_mock)
    await _setup(hass, mock_config_entry)

    def power(key: str) -> float:
        components = _state(hass, key).attributes["price_components"]
        return next(c["priceIncludingVat"] for c in components if c["type"] == "power")

    assert power("current_price") == 0.21
    assert power("next_hour_price") == 0.22
    assert power("highest_price_today") == power("highest_price_today_hour") == 0.33
    assert power("lowest_price_today") == power("lowest_price_today_hour") == 0.1

    current = _state(hass, "current_price").attributes
    assert len(current["prices"]) == 24
    assert current["prices"][0] == {"timestamp": "2026-11-07T00:00:00+01:00", "price": 0.2}
    assert len(current["prices_tomorrow"]) == 24
    assert current["prices_tomorrow"][0] == {
        "timestamp": "2026-11-08T00:00:00+01:00",
        "price": 0.1,
    }
    assert current["today"] == {"priceIncludingVat": 0.315}
    assert current["monthly"] == {"priceIncludingVat": 10.22}
    assert "prices" not in _state(hass, "next_hour_price").attributes


async def test_state_follows_the_clock(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Prices move on at the full hour without a new API call, and roll over at midnight."""
    mock_tibber(aioclient_mock)
    await _setup(hass, mock_config_entry)

    await _move_to(hass, freezer, "2026-11-07 11:00:00+00:00")  # 12:00 local
    assert _state(hass, "current_price").state == "0.32"
    assert _state(hass, "next_hour_price").state == "0.33"

    # 23:30 local: next hour comes from tomorrow's prices
    await _move_to(hass, freezer, "2026-11-07 22:30:00+00:00")
    assert _state(hass, "current_price").state == "0.43"
    assert _state(hass, "next_hour_price").state == "0.1"

    # 00:00 local: tomorrow becomes today
    mock_tibber(aioclient_mock, exc=aiohttp.ClientError("boom"))  # keep the old data
    await _move_to(hass, freezer, "2026-11-07 23:00:00+00:00")
    assert _state(hass, "current_price").state == "0.1"
    assert _state(hass, "highest_price_today").state == "0.33"
    assert _state(hass, "lowest_price_today_hour").state == "2026-11-07T23:00:00+00:00"
    assert _state(hass, "current_price").attributes["prices_tomorrow"] == []


async def test_next_hour_unknown_without_tomorrow(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Before tomorrow's prices are published the last next-hour price is unknown."""
    mock_tibber(aioclient_mock, json=mock_api_data(tomorrow=False))
    await _setup(hass, mock_config_entry)

    await _move_to(hass, freezer, "2026-11-07 22:30:00+00:00")
    assert _state(hass, "current_price").state == "0.43"
    assert _state(hass, "next_hour_price").state == STATE_UNKNOWN


async def test_sensors_unavailable_when_update_fails(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A failed poll marks the sensors unavailable; the next good poll restores them."""
    mock_tibber(aioclient_mock)
    await _setup(hass, mock_config_entry)

    mock_tibber(aioclient_mock, json={"energy": {"todayHours": [{"hour": 1}]}})
    freezer.tick(UPDATE_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    for description in SENSOR_TYPES:
        assert _state(hass, description.key).state == STATE_UNAVAILABLE

    mock_tibber(aioclient_mock)
    freezer.tick(UPDATE_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _state(hass, "current_price").state != STATE_UNAVAILABLE
    assert DOMAIN in hass.config.components
