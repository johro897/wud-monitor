"""WUD Monitor — Home Assistant integration for What's Up Docker."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_POLL_INTERVAL, CONF_PORT, DEFAULT_POLL_INTERVAL, DOMAIN
from .coordinator import WUDCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WUD Monitor from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    poll_interval = entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

    coordinator = WUDCoordinator(hass, host, port, poll_interval)

    # Perform the first refresh before setting up platforms so entities have data immediately
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a WUD Monitor config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
