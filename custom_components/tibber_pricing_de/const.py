"""Constants for the Tibber Pricing DE integration."""

from typing import Final

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONF_NAME, Platform
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

DOMAIN = "tibber_pricing_de"
CONF_POSTALCODE = "postalcode"
DEFAULT_NAME = "Tibber Pricing DE"
TIBBER_API_URL = "https://tibber.com/de/api/lookup/price-overview?postalCode={0}"

SENSOR_PREFIX = "Tibber Pricing DE"

PLATFORMS = [
    Platform.SENSOR,
]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=SENSOR_PREFIX): cv.string,
        vol.Required(CONF_POSTALCODE): cv.string,
    }
)

SENSOR_TYPES: Final[tuple[SensorEntityDescription, ...]] = (
    SensorEntityDescription(
        key="current_price",
        name="Current Price",
        icon="mdi:currency-eur",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.MONETARY,
    ),
    SensorEntityDescription(
        key="next_hour_price",
        name="Next Hour Price",
        icon="mdi:chevron-right",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.MONETARY,
    ),
    SensorEntityDescription(
        key="highest_price_today",
        name="Highest Price Today",
        icon="mdi:gauge-full",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.MONETARY,
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
        device_class=SensorDeviceClass.MONETARY,
    ),
    SensorEntityDescription(
        key="lowest_price_today_hour",
        name="Lowest Price Today Hour",
        icon="mdi:calendar-clock-outline",
        state_class=SensorDeviceClass.TIMESTAMP,
    ),
)
