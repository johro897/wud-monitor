"""WUD Monitor — Home Assistant integration for What's Up Docker."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_HOST,
    CONF_INSTANCE_NAME,
    CONF_POLL_INTERVAL,
    CONF_PORT,
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_USE_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .coordinator import WUDCoordinator
from .sensor import _build_controller_device

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WUD Monitor from a config entry."""
    coordinator = WUDCoordinator(
        hass,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        poll_interval=entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
        auth_config=entry.data,
        use_ssl=entry.data.get(CONF_USE_SSL, DEFAULT_USE_SSL),
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )

    await coordinator.async_config_entry_first_refresh()

    # Register the Controller device up front so compose-project devices can
    # link to it via its registry id (`via_device_id`). The old
    # `via_device=(DOMAIN, identifier)` form is deprecated and stops working
    # in HA 2027.8.0 (#19). Same identifiers/fields as the entities' own
    # device info, so this resolves to the existing device on upgrade.
    controller = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        **_build_controller_device(entry.entry_id, entry.data[CONF_INSTANCE_NAME]),
    )
    coordinator.controller_device_id = controller.id

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its settings change (host, scheme, auth, interval)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a WUD Monitor config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
