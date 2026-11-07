"""Tests for the Tibber Pricing DE config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import aiohttp
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.tibber_pricing_de.const import CONF_POSTALCODE, DOMAIN

from .conftest import POSTALCODE, TITLE, mock_tibber

USER_INPUT = {CONF_POSTALCODE: POSTALCODE}


@pytest.fixture(autouse=True)
def no_setup() -> Any:
    """Do not set up the created entry."""
    with patch("custom_components.tibber_pricing_de.async_setup_entry", return_value=True):
        yield


async def test_user_flow_success(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A known postal code creates an entry keyed on the postal code."""
    mock_tibber(aioclient_mock)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert CONF_POSTALCODE in result["data_schema"].schema

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_POSTALCODE: f" {POSTALCODE} "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TITLE
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == POSTALCODE
    assert aioclient_mock.call_count == 1


@pytest.mark.parametrize("postalcode", ["1234", "123456", "abcde", ""])
async def test_user_flow_invalid_format(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, postalcode: str
) -> None:
    """A malformed postal code is rejected without calling the API."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_POSTALCODE: postalcode}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_POSTALCODE: "invalid_postalcode"}
    assert aioclient_mock.call_count == 0


@pytest.mark.parametrize(
    ("mock_kwargs", "errors"),
    [
        ({"status": 404}, {CONF_POSTALCODE: "unknown_postalcode"}),
        ({"status": 500}, {"base": "cannot_connect"}),
        ({"exc": TimeoutError()}, {"base": "cannot_connect"}),
        ({"exc": aiohttp.ClientError("boom")}, {"base": "cannot_connect"}),
        ({"text": "not json"}, {"base": "invalid_response"}),
        ({"json": {"energy": {}}}, {"base": "invalid_response"}),
        ({"exc": RuntimeError("boom")}, {"base": "unknown"}),
    ],
)
async def test_user_flow_errors_and_recovery(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_kwargs: dict[str, Any],
    errors: dict[str, str],
) -> None:
    """Errors re-show the full form with the input kept; a retry can succeed."""
    mock_tibber(aioclient_mock, **mock_kwargs)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == errors
    schema_keys = {str(key): key for key in result["data_schema"].schema}
    assert schema_keys[CONF_POSTALCODE].description == {"suggested_value": POSTALCODE}

    mock_tibber(aioclient_mock)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_already_configured(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_config_entry: MockConfigEntry
) -> None:
    """The same postal code cannot be added twice."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert aioclient_mock.call_count == 0
