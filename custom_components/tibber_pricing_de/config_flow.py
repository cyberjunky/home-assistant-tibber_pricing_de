import logging

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
import httpx

from .const import CONF_POSTALCODE, DOMAIN, TIBBER_API_URL

_LOGGER = logging.getLogger(__name__)

# type: ignore[misc, call-arg]


class TibberPricingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=self._get_data_schema())

        try:
            url: str = TIBBER_API_URL.format(user_input[CONF_POSTALCODE])
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5)
            _LOGGER.debug("Response status from the Tibber API: %s", response.status_code)
        except httpx.RequestError:
            _LOGGER.error("Cannot connect to the Tibber API")
            return self.async_show_form(step_id="user", errors={"base": "cannot_connect"})
        except httpx.TimeoutException:
            _LOGGER.error("Timeout occurred while trying to connect to the Tibber API")
            return self.async_show_form(step_id="user", errors={"base": "timeout"})
        except Exception as err:
            _LOGGER.error(
                "Unknown error occurred while downloading data from the Tibber API: %s", err
            )
            return self.async_show_form(step_id="user", errors={"base": "unknown"})

        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

    def _get_data_schema(self):
        from homeassistant.helpers import config_validation as cv
        import voluptuous as vol

        return vol.Schema(
            {
                vol.Required(CONF_NAME, default="Tibber Pricing"): str,
                vol.Required(CONF_POSTALCODE): cv.string,
            }
        )
