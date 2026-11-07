"""Sensors for Tibber Pricing DE."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import SLOT_LENGTH, PriceSlot, TibberPrices
from .const import DOMAIN
from .coordinator import TibberPricingConfigEntry, TibberPricingCoordinator

PARALLEL_UPDATES = 0

PRICE_UNIT = f"EUR/{UnitOfEnergy.KILO_WATT_HOUR}"

ATTR_MONTHLY = "monthly"
ATTR_PRICE_COMPONENTS = "price_components"
ATTR_PRICES = "prices"
ATTR_PRICES_TOMORROW = "prices_tomorrow"
ATTR_TODAY = "today"


def _today(data: TibberPrices, now: datetime) -> list[PriceSlot]:
    return data.slots_on(dt_util.as_local(now).date())


def _highest_today(data: TibberPrices, now: datetime) -> PriceSlot | None:
    return max(_today(data, now), key=lambda slot: slot.price, default=None)


def _lowest_today(data: TibberPrices, now: datetime) -> PriceSlot | None:
    return min(_today(data, now), key=lambda slot: slot.price, default=None)


def _price_list(slots: list[PriceSlot]) -> list[dict[str, Any]]:
    return [
        {"timestamp": dt_util.as_local(slot.start).isoformat(), "price": slot.price}
        for slot in slots
    ]


def _overview_attributes(data: TibberPrices, now: datetime) -> dict[str, Any]:
    today = dt_util.as_local(now).date()
    return {
        ATTR_PRICES: _price_list(data.slots_on(today)),
        ATTR_PRICES_TOMORROW: _price_list(data.slots_on(today + timedelta(days=1))),
        ATTR_TODAY: data.today,
        ATTR_MONTHLY: data.monthly_fees,
    }


@dataclass(frozen=True, kw_only=True)
class TibberPricingSensorEntityDescription(SensorEntityDescription):
    """Describe a Tibber Pricing DE sensor."""

    slot_fn: Callable[[TibberPrices, datetime], PriceSlot | None]
    value_fn: Callable[[PriceSlot], float | datetime]
    attributes_fn: Callable[[TibberPrices, datetime], dict[str, Any]] | None = None


def _price(slot: PriceSlot) -> float:
    return slot.price


def _start(slot: PriceSlot) -> datetime:
    return slot.start


SENSOR_TYPES: tuple[TibberPricingSensorEntityDescription, ...] = (
    TibberPricingSensorEntityDescription(
        key="current_price",
        translation_key="current_price",
        native_unit_of_measurement=PRICE_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        slot_fn=lambda data, now: data.slot_at(now),
        value_fn=_price,
        attributes_fn=_overview_attributes,
    ),
    TibberPricingSensorEntityDescription(
        key="next_hour_price",
        translation_key="next_hour_price",
        native_unit_of_measurement=PRICE_UNIT,
        suggested_display_precision=4,
        slot_fn=lambda data, now: data.slot_at(now + SLOT_LENGTH),
        value_fn=_price,
    ),
    TibberPricingSensorEntityDescription(
        key="highest_price_today",
        translation_key="highest_price_today",
        native_unit_of_measurement=PRICE_UNIT,
        suggested_display_precision=4,
        slot_fn=_highest_today,
        value_fn=_price,
    ),
    TibberPricingSensorEntityDescription(
        key="highest_price_today_hour",
        translation_key="highest_price_today_hour",
        device_class=SensorDeviceClass.TIMESTAMP,
        slot_fn=_highest_today,
        value_fn=_start,
    ),
    TibberPricingSensorEntityDescription(
        key="lowest_price_today",
        translation_key="lowest_price_today",
        native_unit_of_measurement=PRICE_UNIT,
        suggested_display_precision=4,
        slot_fn=_lowest_today,
        value_fn=_price,
    ),
    TibberPricingSensorEntityDescription(
        key="lowest_price_today_hour",
        translation_key="lowest_price_today_hour",
        device_class=SensorDeviceClass.TIMESTAMP,
        slot_fn=_lowest_today,
        value_fn=_start,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TibberPricingConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Tibber Pricing DE sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        TibberPricingSensor(coordinator, description) for description in SENSOR_TYPES
    )


class TibberPricingSensor(CoordinatorEntity[TibberPricingCoordinator], SensorEntity):
    """A sensor derived from the hourly Tibber prices."""

    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset(
        {ATTR_MONTHLY, ATTR_PRICE_COMPONENTS, ATTR_PRICES, ATTR_PRICES_TOMORROW, ATTR_TODAY}
    )
    entity_description: TibberPricingSensorEntityDescription

    def __init__(
        self,
        coordinator: TibberPricingCoordinator,
        description: TibberPricingSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Tibber",
            model=f"Price overview {coordinator.postalcode}",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://tibber.com/de",
        )

    async def async_added_to_hass(self) -> None:
        """Refresh the state at every full hour, when the current slot changes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(self.hass, self._async_hour_changed, minute=0, second=0)
        )

    @callback
    def _async_hour_changed(self, _now: datetime) -> None:
        self.async_write_ha_state()

    def _slot(self) -> PriceSlot | None:
        return self.entity_description.slot_fn(self.coordinator.data, dt_util.utcnow())

    @property
    def native_value(self) -> float | datetime | None:
        """Return the state of the sensor."""
        if (slot := self._slot()) is None:
            return None
        return self.entity_description.value_fn(slot)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the price components of the slot and, for some sensors, the overview."""
        slot = self._slot()
        attributes: dict[str, Any] = {ATTR_PRICE_COMPONENTS: slot.components if slot else None}
        if self.entity_description.attributes_fn is not None:
            attributes |= self.entity_description.attributes_fn(
                self.coordinator.data, dt_util.utcnow()
            )
        return attributes
