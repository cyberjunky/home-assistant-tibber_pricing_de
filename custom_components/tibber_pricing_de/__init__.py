"""The Tibber Pricing DE integration."""

from __future__ import annotations

import logging

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import CONF_POSTALCODE, DOMAIN, PLATFORMS
from .coordinator import TibberPricingConfigEntry, TibberPricingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: TibberPricingConfigEntry) -> bool:
    """Set up Tibber Pricing DE from a config entry."""
    coordinator = TibberPricingCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TibberPricingConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: TibberPricingConfigEntry) -> bool:
    """Migrate old config entries. Home Assistant itself refuses downgrades."""
    if entry.version < 3:
        # Version 2 keyed entities on "<name> <key>" and stored the name in data.
        # Version 3 keys them on the entry ID and uses the postal code as unique ID.
        old_prefix = f"{entry.data.get(CONF_NAME) or ''} "
        postalcode = str(entry.data[CONF_POSTALCODE]).strip()

        @callback
        def _migrate_unique_id(reg_entry: er.RegistryEntry) -> dict[str, str] | None:
            if not reg_entry.unique_id.startswith(old_prefix):
                return None
            key = reg_entry.unique_id.removeprefix(old_prefix)
            return {"new_unique_id": f"{entry.entry_id}_{key}"}

        await er.async_migrate_entries(hass, entry.entry_id, _migrate_unique_id)

        unique_id = entry.unique_id
        if unique_id is None and not hass.config_entries.async_entry_for_domain_unique_id(
            DOMAIN, postalcode
        ):
            unique_id = postalcode

        hass.config_entries.async_update_entry(
            entry,
            data={CONF_POSTALCODE: postalcode},
            unique_id=unique_id,
            version=3,
        )
        _LOGGER.debug("Migrated config entry %s to version 3", entry.entry_id)

    return True
