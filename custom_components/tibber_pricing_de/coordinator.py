"""Data update coordinator for Tibber Pricing DE."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TibberError, TibberPrices, async_get_prices
from .const import CONF_POSTALCODE, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type TibberPricingConfigEntry = ConfigEntry[TibberPricingCoordinator]


class TibberPricingCoordinator(DataUpdateCoordinator[TibberPrices]):
    """Fetch the price overview for one postal code."""

    config_entry: TibberPricingConfigEntry

    def __init__(self, hass: HomeAssistant, entry: TibberPricingConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.postalcode: str = entry.data[CONF_POSTALCODE]
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> TibberPrices:
        try:
            return await async_get_prices(self._session, self.postalcode)
        except TibberError as err:
            raise UpdateFailed(str(err)) from err
