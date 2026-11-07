"""Tests for the Tibber Pricing DE config flow."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import httpx
import pytest

from custom_components.tibber_pricing_de.const import CONF_POSTALCODE, DOMAIN

from .conftest import NAME, POSTALCODE, URL

USER_INPUT = {CONF_NAME: NAME, CONF_POSTALCODE: POSTALCODE}


@pytest.fixture
def mock_httpx() -> Generator[AsyncMock]:
    """Patch httpx.AsyncClient used by the config flow; yield the client's get()."""
    client = MagicMock()
    client.get = AsyncMock(return_value=MagicMock(status_code=200))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    with patch(
        "custom_components.tibber_pricing_de.config_flow.httpx.AsyncClient", return_value=ctx
    ):
        yield client.get


async def test_user_flow_success(hass: HomeAssistant, mock_httpx: AsyncMock) -> None:
    """A reachable API creates an entry with the user input as data."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == NAME
    assert result["data"] == USER_INPUT
    mock_httpx.assert_awaited_once_with(URL, timeout=5)


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (httpx.ConnectTimeout("timeout"), "timeout"),
        (httpx.ConnectError("refused"), "cannot_connect"),
        (RuntimeError("boom"), "unknown"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant, mock_httpx: AsyncMock, side_effect: Exception, error: str
) -> None:
    """Connection failures re-show the user step with the mapped error."""
    mock_httpx.side_effect = side_effect

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": error}
