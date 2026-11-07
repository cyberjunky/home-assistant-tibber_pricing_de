"""Fixtures for Tibber Pricing DE tests."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
import sys
import types
from typing import Any
from unittest.mock import patch

from homeassistant.const import CONF_NAME
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.tibber_pricing_de.const import (
    CONF_POSTALCODE,
    DOMAIN,
    TIBBER_API_URL,
)

POSTALCODE = "10115"
NAME = "Tibber Pricing DE"
URL = TIBBER_API_URL.format(POSTALCODE)
TODAY = "2026-11-07"
# 11:30 local time in Europe/Berlin (CET, UTC+1)
FROZEN_TIME = "2026-11-07 10:30:00+00:00"


def mock_api_data() -> dict[str, Any]:
    """Return a Tibber price-overview payload with 24 hourly prices for TODAY."""
    return {
        "energy": {
            "todayHours": [
                {
                    "hour": hour,
                    "date": TODAY,
                    "priceIncludingVat": round(0.20 + hour / 100, 2),
                    "priceComponents": [{"type": "grid", "priceIncludingVat": 0.1}],
                }
                for hour in range(24)
            ],
            "today": {"min": 0.20, "max": 0.43},
        },
        "monthlyFees": {"baseFee": 5.99},
    }


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom_components in every test."""


@pytest.fixture
def async_timeout_shim() -> Generator[None]:
    """Provide a stand-in ``async_timeout`` module if it is not installed.

    ``sensor.py`` imports the third-party ``async_timeout`` package, which
    Home Assistant no longer installs. Without it the config entry fails to
    set up. This shim lets the sensor logic be tested until the import is
    replaced by ``asyncio.timeout``; ``test_init.test_sensor_module_imports``
    tracks the bug.
    """
    try:
        import async_timeout  # noqa: F401
    except ModuleNotFoundError:
        shim = types.ModuleType("async_timeout")
        shim.timeout = asyncio.timeout  # type: ignore[attr-defined]
        with patch.dict(sys.modules, {"async_timeout": shim}):
            yield
        return
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry for one postal code."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        version=2,
        data={CONF_NAME: NAME, CONF_POSTALCODE: POSTALCODE},
        entry_id="test_entry_id",
    )


def mock_tibber(aioclient_mock: AiohttpClientMocker, **kwargs: Any) -> None:
    """Register the Tibber price endpoint on the aiohttp mocker."""
    aioclient_mock.clear_requests()
    if not kwargs:
        kwargs = {"json": mock_api_data()}
    aioclient_mock.get(URL, **kwargs)
