"""Support for Tibber Pricing sensors."""

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any, Optional
from zoneinfo import ZoneInfo

import aiohttp
import async_timeout
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import Throttle

from .const import CONF_POSTALCODE, SENSOR_TYPES, TIBBER_API_URL

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(hours=1)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tibber Pricing sensors from a config entry."""
    config = config_entry.data
    postalcode = config[CONF_POSTALCODE]
    default_name = config[CONF_NAME]

    if postalcode is None:
        _LOGGER.error("Postal code is missing in the configuration entry")
        return

    if default_name is None:
        _LOGGER.error("Name is missing in the configuration entry")
        return

    session = async_get_clientsession(hass)
    data = TibberData(session, postalcode)

    try:
        await data.async_update()
    except ValueError as err:
        _LOGGER.error("Error while fetching data from Tibber API: %s", err)
        return

    entities = []
    for description in SENSOR_TYPES:
        sensor = TibberPricingSensor(
            description, data, default_name, hass.config.time_zone)
        entities.append(sensor)

    async_add_entities(entities, True)


class TibberData:
    """Handle Tibber data object and limit updates."""

    def __init__(self, session: aiohttp.ClientSession, postalcode: str) -> None:
        """Initialize."""

        self._session: aiohttp.ClientSession = session
        self._postalcode: str = postalcode
        self._data: Optional[dict[str, Any]] = None

    @property
    def latest_data(self) -> Optional[dict[str, Any]]:
        """Return the latest data object."""
        return self._data

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self) -> None:
        """Get the pricing data."""

        pricing_data: dict[str, Any] = {}
        prices_data: list[dict[str, Any]] = []
        try:
            url: str = TIBBER_API_URL.format(self._postalcode)
            async with async_timeout.timeout(5):
                response: aiohttp.ClientResponse = await self._session.get(url)
            _LOGGER.debug(
                "Response status from the Tibber API: %s", response.status)
        except aiohttp.ClientError:
            _LOGGER.error("Cannot connect to the Tibber API")
            self._data = None
            return
        except asyncio.TimeoutError:
            _LOGGER.error(
                "Timeout occurred while trying to connect to the Tibber API")
            self._data = None
            return
        except Exception as err:
            _LOGGER.error(
                "Unknown error occurred while downloading data from the Tibber API: %s",
                err,
            )
            self._data = None
            return

        try:
            json_data: dict[str, Any] = await response.json()
            _LOGGER.debug("Data received from Tibber API: %s", json_data)
        except Exception as err:
            _LOGGER.error("Cannot parse data from Tibber API: %s", err)
            self._data = None
            return

        # Parse the Tibber API data.
        try:
            for pricing in json_data["energy"]["todayHours"]:
                _LOGGER.debug(
                    "todayHours hour: %s date: %s priceIncludingVat: %s priceComponents: %s",
                    pricing["hour"],
                    pricing["date"],
                    pricing["priceIncludingVat"],
                    pricing["priceComponents"],
                )
                price: dict[str, Any] = {}
                # Ensure the hour is always two digits
                formatted_hour = str(pricing["hour"]).zfill(2)
                price["timestamp"] = f"{pricing['date']} {formatted_hour}:00:00"
                price["price"] = pricing["priceIncludingVat"]
                price["priceComponents"] = pricing["priceComponents"]
                prices_data.append(price)

            pricing_data["prices"] = prices_data
            pricing_data["monthly"] = json_data["monthlyFees"]
            pricing_data["today"] = json_data["energy"]["today"]

            self._data = pricing_data
        except ValueError as err:
            _LOGGER.error("Cannot parse the Tibber API data %s", err.args)
            self._data = None


class TibberPricingSensor(Entity):
    """Representation of a Tibber Sensor."""

    def __init__(
        self,
        description: SensorEntityDescription,
        data: TibberData,
        default_name: str,
        time_zone: str,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description: SensorEntityDescription = description
        self._data: TibberData = data
        self._time_zone = time_zone
        self._default_name: str = default_name if default_name else ""

        self._state: Optional[Any] = None
        self._type: str = self.entity_description.key
        self._name: str = str(self.entity_description.name)
        self._attr_icon: str = self.entity_description.icon or "mdi:currency-eur"
        self._attr_name: str = self._default_name + \
            " " + (self._name if self._name else "")
        self._attr_unique_id: str = f"{self._default_name} {self._type}"
        self._local_timezone = ZoneInfo(self._time_zone)

        self._discovery = False
        self._pricing_data: Optional[dict[str, Any]] = None

    @property
    def state(self) -> Optional[Any]:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> Optional[dict[str, Any]]:
        """Return the state attributes of this device."""

        # Get the current time with the local timezone
        now: datetime = datetime.now(self._local_timezone)
        timestamp: str = now.strftime("%Y-%m-%d %H:00:00+02:00")

        # Find the matching entry
        matching_entry: Optional[dict[str, Any]] = None
        if self._pricing_data and self._pricing_data["prices"]:
            for pricing in self._pricing_data["prices"]:
                if pricing["timestamp"] == timestamp:
                    matching_entry = pricing
                    break

        if self._type == "current_price":
            return {
                "prices": self._pricing_data["prices"] if self._pricing_data else None,
                "price_components": matching_entry["priceComponents"] if matching_entry else None,
                "today": self._pricing_data["today"] if self._pricing_data else None,
                "monthly": self._pricing_data["monthly"] if self._pricing_data else None,
            }

        return {
            "price_components": matching_entry["priceComponents"] if matching_entry else None,
        }

    async def async_update(self) -> None:
        """Get the latest data and use it to update our sensor state."""

        await self._data.async_update()
        self._pricing_data = self._data.latest_data

        # Initialize variables
        highest_price: Optional[float] = None
        lowest_price: Optional[float] = None
        highest_price_timestamp: str = ""
        lowest_price_timestamp: str = ""
        now = datetime.now(self._local_timezone) + timedelta(hours=1)

        # This hour price including taxes
        if self._type == "current_price":
            # Get the current time with the local timezone
            timestamp: str = now.strftime("%Y-%m-%d %H:00:00")

            # Find the matching entry
            matching_entry: Optional[dict[str, Any]] = None
            if self._pricing_data:
                for pricing in self._pricing_data["prices"]:
                    if pricing["timestamp"] == timestamp:
                        matching_entry = pricing
                        break

            self._state = matching_entry["price"] if matching_entry else None

        # Next hour price including taxes
        if self._type == "next_hour_price":
            # Get the current time with the local timezone
            one_hour_later = now + timedelta(hours=1)

            # Format the result as a string
            timestamp = one_hour_later.strftime("%Y-%m-%d %H:00:00")

            # Find the matching entry
            matching_entry = None
            if self._pricing_data:
                for pricing in self._pricing_data["prices"]:
                    if pricing["timestamp"] == timestamp:
                        matching_entry = pricing
                        break

            self._state = matching_entry["price"] if matching_entry else None

        # Highest price today including taxes
        if self._type == "highest_price_today":
            if self._pricing_data:
                for price_data in self._pricing_data["prices"]:
                    price = price_data["price"]

                    if highest_price is None or price > highest_price:
                        highest_price = price

                    if lowest_price is None or price < lowest_price:
                        lowest_price = price

                self._state = highest_price

        if self._type == "lowest_price_today":
            if self._pricing_data:
                for price_data in self._pricing_data["prices"]:
                    price = price_data["price"]

                    if highest_price is None or price > highest_price:
                        highest_price = price

                    if lowest_price is None or price < lowest_price:
                        lowest_price = price

                self._state = lowest_price

        if self._type == "highest_price_today_hour":
            if self._pricing_data:
                for price_data in self._pricing_data["prices"]:
                    price = price_data["price"]
                    timestamp = price_data["timestamp"]

                    if highest_price is None or price > highest_price:
                        highest_price = price
                        highest_price_timestamp = timestamp

                    if lowest_price is None or price < lowest_price:
                        lowest_price = price
                        lowest_price_timestamp = timestamp

                self._state = highest_price_timestamp

        if self._type == "lowest_price_today_hour":
            if self._pricing_data:
                for price_data in self._pricing_data["prices"]:
                    price = price_data["price"]
                    timestamp = price_data["timestamp"]

                    if highest_price is None or price > highest_price:
                        highest_price = price
                        highest_price_timestamp = timestamp

                    if lowest_price is None or price < lowest_price:
                        lowest_price = price
                        lowest_price_timestamp = timestamp

                self._state = lowest_price_timestamp

        _LOGGER.debug("Device: %s State: %s", self._attr_name, self._state)
