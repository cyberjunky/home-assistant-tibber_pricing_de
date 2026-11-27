"""Constants for the Tibber Pricing DE integration."""

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "tibber_pricing_de"
PLATFORMS: Final = [Platform.SENSOR]

CONF_POSTALCODE: Final = "postalcode"
DEFAULT_NAME: Final = "Tibber Pricing DE"

TIBBER_API_URL: Final = "https://tibber.com/de/api/lookup/price-overview?postalCode={0}"
# The price-overview endpoint reports dates and hours in German local time.
TIBBER_TIME_ZONE: Final = "Europe/Berlin"
REQUEST_TIMEOUT: Final = 10

# Day-ahead prices for tomorrow are published around 13:00, so hourly polling
# picks them up in time while keeping the request rate low.
UPDATE_INTERVAL: Final = timedelta(hours=1)
