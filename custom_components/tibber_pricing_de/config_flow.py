"""Config flow for the Tibber Pricing DE integration."""

from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import (
    TibberConnectionError,
    TibberInvalidResponseError,
    TibberPostalCodeError,
    async_get_prices,
)
from .const import CONF_POSTALCODE, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

POSTALCODE_PATTERN = re.compile(r"\d{5}")
DATA_SCHEMA = vol.Schema({vol.Required(CONF_POSTALCODE): str})


class TibberPricingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Tibber Pricing DE config flow."""

    VERSION = 3

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the postal code and validate it against the Tibber API."""
        errors: dict[str, str] = {}

        if user_input is not None:
            postalcode = user_input[CONF_POSTALCODE].strip()
            if not POSTALCODE_PATTERN.fullmatch(postalcode):
                errors[CONF_POSTALCODE] = "invalid_postalcode"
            else:
                await self.async_set_unique_id(postalcode)
                self._abort_if_unique_id_configured()
                try:
                    await async_get_prices(async_get_clientsession(self.hass), postalcode)
                except TibberPostalCodeError:
                    errors[CONF_POSTALCODE] = "unknown_postalcode"
                except TibberConnectionError:
                    errors["base"] = "cannot_connect"
                except TibberInvalidResponseError:
                    errors["base"] = "invalid_response"
                except Exception:
                    _LOGGER.exception("Unexpected error while validating the postal code")
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(
                        title=f"{DEFAULT_NAME} {postalcode}",
                        data={CONF_POSTALCODE: postalcode},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(DATA_SCHEMA, user_input),
            errors=errors,
        )
