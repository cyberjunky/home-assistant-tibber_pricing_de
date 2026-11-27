"""Fixtures for Tibber Pricing DE tests."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.tibber_pricing_de.const import (
    CONF_POSTALCODE,
    DOMAIN,
    TIBBER_API_URL,
)

POSTALCODE = "10115"
TITLE = "Tibber Pricing DE 10115"
URL = TIBBER_API_URL.format(POSTALCODE)
TODAY = "2026-11-07"
TOMORROW = "2026-11-08"
# 11:30 local time in Europe/Berlin (CET, UTC+1)
FROZEN_TIME = "2026-11-07 10:30:00+00:00"


def _hours(day: str, base: float) -> list[dict[str, Any]]:
    return [
        {
            "hour": hour,
            "date": day,
            "priceExcludingVat": round((base + hour / 100) / 1.19, 4),
            "priceIncludingVat": round(base + hour / 100, 2),
            "priceComponents": [
                {"type": "power", "priceIncludingVat": round(base - 0.1 + hour / 100, 2)},
                {"type": "grid", "priceIncludingVat": 0.1},
            ],
        }
        for hour in range(24)
    ]


def mock_api_data(*, tomorrow: bool = True) -> dict[str, Any]:
    """Return a price-overview payload: today 0.20..0.43, tomorrow 0.10..0.33 EUR/kWh."""
    return {
        "priceArea": "DE",
        "currency": "EUR",
        "energy": {
            "todayHours": _hours(TODAY, 0.20),
            "tomorrowHours": _hours(TOMORROW, 0.10) if tomorrow else [],
            "today": {"priceIncludingVat": 0.315},
        },
        "monthlyFees": {"priceIncludingVat": 10.22},
    }


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom_components in every test."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry for one postal code."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=TITLE,
        version=3,
        unique_id=POSTALCODE,
        data={CONF_POSTALCODE: POSTALCODE},
        entry_id="test_entry_id",
    )


def mock_tibber(aioclient_mock: AiohttpClientMocker, **kwargs: Any) -> None:
    """Register the Tibber price endpoint on the aiohttp mocker."""
    aioclient_mock.clear_requests()
    if not kwargs:
        kwargs = {"json": mock_api_data()}
    aioclient_mock.get(URL, **kwargs)
