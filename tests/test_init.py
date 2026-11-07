"""Tests for Tibber Pricing DE setup and unload."""

from __future__ import annotations

import importlib
import sys

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.tibber_pricing_de.const import DOMAIN

from .conftest import mock_tibber


@pytest.mark.xfail(
    strict=True,
    reason="sensor.py imports async_timeout, which Home Assistant no longer ships",
)
def test_sensor_module_imports() -> None:
    """The sensor platform must import with only Home Assistant's dependencies."""
    sys.modules.pop("custom_components.tibber_pricing_de.sensor", None)
    importlib.import_module("custom_components.tibber_pricing_de.sensor")


@pytest.mark.usefixtures("async_timeout_shim")
async def test_setup_and_unload_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    """The entry loads, stores its data, and unloads cleanly."""
    mock_config_entry.add_to_hass(hass)
    mock_tibber(aioclient_mock)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert hass.data[DOMAIN][mock_config_entry.entry_id] == mock_config_entry.data
    assert len(hass.states.async_entity_ids("sensor")) == 6

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]
