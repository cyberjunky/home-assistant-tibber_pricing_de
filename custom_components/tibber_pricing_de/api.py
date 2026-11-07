"""Client for the public Tibber price-overview endpoint."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from http import HTTPStatus
from typing import Any

import aiohttp
from homeassistant.util import dt as dt_util

from .const import REQUEST_TIMEOUT, TIBBER_API_URL, TIBBER_TIME_ZONE

SLOT_LENGTH = timedelta(hours=1)
_API_TZ = dt_util.get_time_zone(TIBBER_TIME_ZONE)


class TibberError(Exception):
    """Base error for the Tibber price-overview client."""


class TibberConnectionError(TibberError):
    """The endpoint could not be reached or returned an HTTP error."""


class TibberPostalCodeError(TibberError):
    """The endpoint does not know the postal code."""


class TibberInvalidResponseError(TibberError):
    """The endpoint returned a payload that cannot be parsed."""


@dataclass(frozen=True, slots=True)
class PriceSlot:
    """Price for one hour, including VAT."""

    start: datetime
    price: float
    components: list[dict[str, Any]]

    @property
    def end(self) -> datetime:
        """Return the end of the slot (exclusive)."""
        return self.start + SLOT_LENGTH


@dataclass(frozen=True, slots=True)
class TibberPrices:
    """Parsed price overview for one postal code."""

    slots: list[PriceSlot]
    today: dict[str, Any]
    monthly_fees: dict[str, Any]

    def slot_at(self, moment: datetime) -> PriceSlot | None:
        """Return the slot that contains ``moment``."""
        return next((slot for slot in self.slots if slot.start <= moment < slot.end), None)

    def slots_on(self, day: date) -> list[PriceSlot]:
        """Return the slots that start on ``day`` in Home Assistant's time zone."""
        return [slot for slot in self.slots if dt_util.as_local(slot.start).date() == day]


def _parse_slots(hours: list[dict[str, Any]]) -> list[PriceSlot]:
    slots = []
    for item in hours:
        day = date.fromisoformat(item["date"])
        local_start = datetime(day.year, day.month, day.day, int(item["hour"]), tzinfo=_API_TZ)
        slots.append(
            PriceSlot(
                start=local_start.astimezone(UTC),
                price=float(item["priceIncludingVat"]),
                components=list(item.get("priceComponents") or []),
            )
        )
    return slots


def parse_prices(payload: Any) -> TibberPrices:
    """Parse a price-overview payload, raising TibberInvalidResponseError if malformed."""
    try:
        energy = payload["energy"]
        slots = _parse_slots(energy["todayHours"]) + _parse_slots(energy.get("tomorrowHours") or [])
        return TibberPrices(
            slots=sorted(slots, key=lambda slot: slot.start),
            today=energy.get("today") or {},
            monthly_fees=payload.get("monthlyFees") or {},
        )
    except (AttributeError, KeyError, TypeError, ValueError) as err:
        raise TibberInvalidResponseError(f"Unexpected price data: {err!r}") from err


async def async_get_prices(session: aiohttp.ClientSession, postalcode: str) -> TibberPrices:
    """Fetch and parse the price overview for ``postalcode``."""
    try:
        async with (
            asyncio.timeout(REQUEST_TIMEOUT),
            session.get(TIBBER_API_URL.format(postalcode)) as response,
        ):
            if response.status == HTTPStatus.NOT_FOUND:
                raise TibberPostalCodeError(f"Unknown postal code {postalcode}")
            response.raise_for_status()
            payload = await response.json(content_type=None)
    except TimeoutError as err:
        raise TibberConnectionError("Timeout while connecting to the Tibber API") from err
    except aiohttp.ClientError as err:
        raise TibberConnectionError(f"Error while connecting to the Tibber API: {err}") from err
    except ValueError as err:
        raise TibberInvalidResponseError("The Tibber API did not return JSON") from err
    return parse_prices(payload)
