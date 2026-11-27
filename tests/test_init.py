"""Tests for Tibber Pricing DE setup, unload and migration."""

from __future__ import annotations

import importlib
import sys

import aiohttp
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.tibber_pricing_de.const import CONF_POSTALCODE, DOMAIN
from custom_components.tibber_pricing_de.coordinator import TibberPricingCoordinator

from .conftest import POSTALCODE, mock_tibber


def test_sensor_module_imports() -> None:
    """The sensor platform imports with only Home Assistant's dependencies."""
    sys.modules.pop("custom_components.tibber_pricing_de.sensor", None)
    importlib.import_module("custom_components.tibber_pricing_de.sensor")


async def test_setup_and_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    device_registry: dr.DeviceRegistry,
) -> None:
    """The entry loads with a coordinator in runtime_data and unloads cleanly."""
    mock_config_entry.add_to_hass(hass)
    mock_tibber(aioclient_mock)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert isinstance(mock_config_entry.runtime_data, TibberPricingCoordinator)
    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 6

    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, mock_config_entry.entry_id), mock_config_entry.entry_id
    )
    assert device is not None
    assert device.name == mock_config_entry.title
    assert device.entry_type is dr.DeviceEntryType.SERVICE

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_when_api_unreachable(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    """A failing first refresh puts the entry in setup-retry instead of creating dead sensors."""
    mock_config_entry.add_to_hass(hass)
    mock_tibber(aioclient_mock, exc=aiohttp.ClientError("boom"))

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
    assert hass.states.async_entity_ids(SENSOR_DOMAIN) == []


async def test_migrate_v2_entry(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    entity_registry: er.EntityRegistry,
) -> None:
    """Version 2 entries keep their entities and gain the postal code as unique ID."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="My Tibber",
        version=2,
        data={CONF_NAME: "My Tibber", CONF_POSTALCODE: POSTALCODE},
    )
    entry.add_to_hass(hass)
    old = entity_registry.async_get_or_create(
        SENSOR_DOMAIN,
        DOMAIN,
        "My Tibber current_price",
        config_entry=entry,
        suggested_object_id="my_tibber_current_price",
    )
    other = entity_registry.async_get_or_create(
        SENSOR_DOMAIN, DOMAIN, "Someone else current_price", config_entry=entry
    )
    mock_tibber(aioclient_mock)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 3
    assert entry.unique_id == POSTALCODE
    assert dict(entry.data) == {CONF_POSTALCODE: POSTALCODE}
    migrated = entity_registry.async_get(old.entity_id)
    assert migrated is not None
    assert migrated.unique_id == f"{entry.entry_id}_current_price"
    assert hass.states.get("sensor.my_tibber_current_price") is not None
    unchanged = entity_registry.async_get(other.entity_id)
    assert unchanged is not None
    assert unchanged.unique_id == "Someone else current_price"


async def test_migrate_v2_duplicate_postalcode(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    """A duplicate postal code is migrated without stealing the existing unique ID."""
    mock_config_entry.add_to_hass(hass)
    duplicate = MockConfigEntry(
        domain=DOMAIN,
        title="Duplicate",
        version=2,
        data={CONF_NAME: "Duplicate", CONF_POSTALCODE: POSTALCODE},
    )
    duplicate.add_to_hass(hass)
    mock_tibber(aioclient_mock)

    assert await hass.config_entries.async_setup(duplicate.entry_id)
    await hass.async_block_till_done()
    assert duplicate.version == 3
    assert duplicate.unique_id is None


async def test_migrate_from_future_version_fails(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Entries from a newer version are not downgraded."""
    entry = MockConfigEntry(domain=DOMAIN, version=4, data={CONF_POSTALCODE: POSTALCODE})
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.MIGRATION_ERROR
