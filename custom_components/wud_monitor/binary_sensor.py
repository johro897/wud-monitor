"""Binary sensor platform for WUD Monitor."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_INSTANCE_NAME, DOMAIN
from .coordinator import WUDCoordinator
from .sensor import _build_container_device, _get_error_message

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WUD Monitor binary sensors from a config entry."""
    coordinator: WUDCoordinator = hass.data[DOMAIN][entry.entry_id]
    instance_name = entry.data[CONF_INSTANCE_NAME]

    entities: list[BinarySensorEntity] = [
        WUDContainerProblemBinarySensor(coordinator, entry, instance_name, container)
        for container in coordinator.data or []
    ]
    async_add_entities(entities)


class WUDContainerProblemBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor (device_class `problem`) that turns on when WUD reports
    an error for this container — lets users automate directly on "this
    container is broken" instead of templating the sensor's `error` attribute."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: WUDCoordinator,
        entry: ConfigEntry,
        instance_name: str,
        container: dict,
    ) -> None:
        """Initialize the problem binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._container_name = container["name"]
        self._container_watcher = container.get("watcher", "docker")

        self._attr_name = f"{container['name']} Problem"

        # Stable unique_id — uses entry_id + watcher + name, same scheme as
        # WUDContainerSensor. Container ID changes on every redeploy; watcher
        # and name do not.
        self._attr_unique_id = (
            f"wud_{entry.entry_id}_{self._container_watcher}_{self._container_name}_problem"
        )

        self._attr_device_info = _build_container_device(
            entry.entry_id, instance_name, container
        )

    def _get_container(self) -> dict | None:
        """Find this container's current data via the coordinator's cached lookup."""
        return self.coordinator.container_by_key.get(
            (self._container_name, self._container_watcher)
        )

    @property
    def available(self) -> bool:
        """Unavailable if the coordinator poll itself failed, or if this specific
        container has disappeared from WUD's payload (renamed/removed)."""
        return super().available and self._get_container() is not None

    @property
    def is_on(self) -> bool | None:
        """Return True if WUD reported an error for this container.

        Returns None (combined with `available` above) when the container is
        no longer present in WUD's payload, same pattern as WUDContainerSensor.
        """
        container = self._get_container()
        if not container:
            return None
        return _get_error_message(container) is not None

    @property
    def extra_state_attributes(self) -> dict:
        """Return the WUD error message, if any."""
        container = self._get_container()
        if not container:
            return {}
        error_message = _get_error_message(container)
        return {"error": error_message} if error_message else {}
