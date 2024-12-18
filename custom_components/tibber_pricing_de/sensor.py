"""
Support for reading Tibber's dynamic pricing data for a German postal code.

configuration.yaml

sensor:
    - platform: tibber_pricing_de
        name: Hartmanssdorf
        postalcode: 07586
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Final

import aiohttp
import async_timeout
import homeassistant.helpers.config_validation as cv
import pytz
import voluptuous as vol
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

TIBBER_API_URL = "https://tibber.com/de/api/lookup/price-overview?postalCode={0}"
_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(hours=1)

SENSOR_PREFIX = "Tibber Pricing"
CONST_POSTALCODE = "postalcode"

# https://github.com/JaccoR/hass-entso-e/blob/main/custom_components/entsoe/sensor.py

SENSOR_TYPES: Final[tuple[SensorEntityDescription, ...]] = (
    SensorEntityDescription(
        key="current_price",
        name="Current Price",
        icon="mdi:currency-eur",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="next_hour_price",
        name="Next Hour Price",
        icon="mdi:chevron-right",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="highest_price_today",
        name="Highest Price Today",
        icon="mdi:gauge-full",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="highest_price_today_hour",
        name="Highest Price Today Hour",
        icon="mdi:calendar-clock-outline",
        state_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="lowest_price_today",
        name="Lowest Price Today",
        icon="mdi:gauge-empty",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="lowest_price_today_hour",
        name="Lowest Price Today Hour",
        icon="mdi:calendar-clock-outline",
        state_class=SensorDeviceClass.TIMESTAMP,
    ),
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=SENSOR_PREFIX): cv.string,
        vol.Required(CONST_POSTALCODE): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup the Tibber Pricing sensors."""

    # scan_interval = config.get(CONF_SCAN_INTERVAL)
    postalcode = config.get(CONST_POSTALCODE)
    default_name = config.get(CONF_NAME)

    session = async_get_clientsession(hass)

    data = TibberData(session, postalcode)
    try:
        await data.async_update()
    except ValueError as err:
        _LOGGER.error("Error while fetching data from Tibber API: %s", err)
        return

    entities = []
    for description in SENSOR_TYPES:
        sensor = TibberSensor(description, data, default_name)
        entities.append(sensor)

    async_add_entities(entities, True)


# pylint: disable=abstract-method
class TibberData:
    """Handle Tibber data object and limit updates."""

    def __init__(self, session, postalcode):
        """Initialize."""

        self._session = session
        self._postalcode = postalcode
        self._data = None

    @property
    def latest_data(self):
        """Return the latest data object."""
        if self._data:
            return self._data
        return None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Get the pricing data."""

        pricing_data = {}
        prices_data = []
        try:
            url = TIBBER_API_URL.format(self._postalcode)
            with async_timeout.timeout(5):
                response = await self._session.get(url)
            _LOGGER.debug("Response status from the Tibber API: %s", response.status)
        except aiohttp.ClientError:
            _LOGGER.error("Cannot connect to the Tibber API")
            self._data = None
            return
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout occurred while trying to connect to the Tibber API")
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
            json_data = await response.json()
            _LOGGER.debug("Data received from Tibber API: %s", json_data)
        except Exception as err:
            _LOGGER.error("Cannot parse data from Tibber API: %s", err)
            self._data = None
            return

        """Parse the Tibber API data."""
        try:
            for pricing in json_data["energy"]["todayHours"]:
                _LOGGER.debug(
                    "todayHours hour: %s date: %s priceIncludingVat: %s priceComponents: %s",
                    pricing["hour"],
                    pricing["date"],
                    pricing["priceIncludingVat"],
                    pricing["priceComponents"],
                )
                price = {}
                # Ensure the hour is always two digits
                formatted_hour = str(pricing["hour"]).zfill(2)
                price["timestamp"] = f"{pricing['date']} {formatted_hour}:00:00+02:00"
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
            return False


"""
prices: 
- timestamp: '2024-10-20 22:00:00+00:00'
    price: 0
- timestamp: '2024-10-20 23:00:00+00:00'
    price: 0
- timestamp: '2024-10-21 00:00:00+00:00'
    price: 0
- timestamp: '2024-10-21 01:00:00+00:00'
    price: 0
- timestamp: '2024-10-21 02:00:00+00:00'
    price: 0
- timestamp: '2024-10-21 03:00:00+00:00'
    price: 0
- timestamp: '2024-10-21 04:00:00+00:00'
    price: 0.07
- timestamp: '2024-10-21 05:00:00+00:00'
    price: 0.12
"""
"""
"energy": {
        "todayHours": [
            {
                "hour": 0,
                "date": "2024-10-21",
                "priceIncludingVat": 0.1683,
                "priceExcludingVat": 0.1414,
                "priceComponents": [
                    {
                        "type": "taxes",
                        "priceExcludingVat": 0.0675,
                        "priceIncludingVat": 0.0803
                    },
                    {
                        "type": "power",
                        "priceExcludingVat": -0.0001,
                        "priceIncludingVat": -0.0001
                    },
                    {
                        "type": "grid",
                        "priceIncludingVat": 0.08806,
                        "priceExcludingVat": 0.074
                    }
                ]
            },
...
        "monthlyFees": {
                "priceExcludingVat": 13.14,
                "priceIncludingVat": 15.64,
                "priceComponents": [
                    {
                        "type": "tibber service fee",
                        "priceExcludingVat": 5.03,
                        "priceIncludingVat": 5.99
                    },
                    {
                        "type": "meter operator",
                        "priceExcludingVat": 0.81,
                        "priceIncludingVat": 0.96
                    },
                    {
                        "type": "grid",
                        "priceExcludingVat": 7.3,
                        "priceIncludingVat": 8.69
                    }
                ]
            }
...
        "today": {
            "priceExcludingVat": 0.2245,
            "priceIncludingVat": 0.2672,
            "priceComponents": [
                {
                    "type": "taxes",
                    "priceExcludingVat": 0.0675,
                    "priceIncludingVat": 0.0803
                },
                {
                    "type": "power",
                    "priceExcludingVat": 0.083,
                    "priceIncludingVat": 0.0988
                },
                {
                    "type": "grid",
                    "priceIncludingVat": 0.08806,
                    "priceExcludingVat": 0.074
                }
            ]
        },
"""


class TibberSensor(Entity):
    """Representation of a Tibber Sensor."""

    def __init__(self, description, data, default_name):
        """Initialize the sensor."""
        self.entity_description = description
        self._data = data

        self._default_name = default_name
        self._state = None

        self._type = self.entity_description.key
        self._attr_icon = self.entity_description.icon
        self._attr_name = self._default_name + " " + self.entity_description.name
        self._attr_unique_id = f"{self._default_name} {self._type}"

        self._discovery = False

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of this device."""

        # Get the local timezone
        local_timezone = pytz.timezone(
            "Europe/Amsterdam"
        )  # Replace with your local timezone

        # Get the current time with the local timezone
        now = datetime.now(local_timezone)
        timestamp = now.strftime("%Y-%m-%d %H:00:00+02:00")

        # Find the matching entry
        matching_entry = None
        for pricing in self._pricing_data["prices"]:
            if pricing["timestamp"] == timestamp:
                matching_entry = pricing
                break

        if self._type == "current_price":
            return {
                "prices": self._pricing_data["prices"],
                "price_components": matching_entry["priceComponents"],
                "today": self._pricing_data["today"],
                "monthly": self._pricing_data["monthly"],
            }

        return {
            "price_components": matching_entry["priceComponents"],
        }

    async def async_update(self):
        """Get the latest data and use it to update our sensor state."""

        await self._data.async_update()
        self._pricing_data = self._data.latest_data

        """This hour price including taxes."""
        if self._type == "current_price":
            # Get the local timezone
            local_timezone = pytz.timezone(
                "Europe/Amsterdam"
            )  # Replace with your local timezone

            # Get the current time with the local timezone
            now = datetime.now(local_timezone)
            # now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d %H:00:00+02:00")

            # Find the matching entry
            matching_entry = None
            for pricing in self._pricing_data["prices"]:
                if pricing["timestamp"] == timestamp:
                    matching_entry = pricing
                    break

            self._state = matching_entry["price"]

        """Next hour price including taxes."""
        if self._type == "next_hour_price":
            # Get the local timezone
            local_timezone = pytz.timezone(
                "Europe/Amsterdam"
            )  # Replace with your local timezone

            # Get the current time with the local timezone
            now = datetime.now(local_timezone)

            # now = datetime.now()
            one_hour_later = now + timedelta(hours=1)

            # Format the result as a string
            timestamp = one_hour_later.strftime("%Y-%m-%d %H:00:00+02:00")

            # Find the matching entry
            matching_entry = None
            for pricing in self._pricing_data["prices"]:
                if pricing["timestamp"] == timestamp:
                    matching_entry = pricing
                    break

            self._state = matching_entry["price"]

        """Highest price today including taxes."""
        if self._type == "highest_price_today":
            # Initialize variables
            highest_price = None
            lowest_price = None

            for price_data in self._pricing_data["prices"]:
                price = price_data["price"]

                if highest_price is None or price > highest_price:
                    highest_price = price

                if lowest_price is None or price < lowest_price:
                    lowest_price = price

            self._state = highest_price

        if self._type == "lowest_price_today":
            # Initialize variables
            highest_price = None
            lowest_price = None

            for price_data in self._pricing_data["prices"]:
                price = price_data["price"]

                if highest_price is None or price > highest_price:
                    highest_price = price

                if lowest_price is None or price < lowest_price:
                    lowest_price = price

            self._state = lowest_price

        if self._type == "highest_price_today_hour":
            # Initialize variables
            highest_price = None
            lowest_price = None

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
            # Initialize variables
            highest_price = None
            lowest_price = None

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

        _LOGGER.debug(f"Device: {self._attr_name} State: {self._state}")
