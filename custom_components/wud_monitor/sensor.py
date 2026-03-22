"""Sensor platform for WUD Monitor."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from homeassistant.util import dt as dt_util

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_INSTANCE_NAME, CONTROLLER_DEVICE_SUFFIX, DOMAIN
from .coordinator import WUDCoordinator

_LOGGER = logging.getLogger(__name__)


def _get_compose_project(container: dict) -> str | None:
    """Extract the Docker Compose project name from container labels."""
    labels = container.get("labels", {}) or {}
    return labels.get("com.docker.compose.project")


def _get_current_version(container: dict) -> str:
    """
    Return the currently running version.
    Prefers org.opencontainers.image.version from labels (e.g. '2026.2.4')
    over image.tag.value which may be truncated (e.g. '2026.2').
    """
    labels = container.get("labels", {}) or {}
    oci_version = labels.get("org.opencontainers.image.version")
    if oci_version:
        return oci_version
    image = container.get("image", {}) or {}
    tag = image.get("tag", {}) or {}
    return tag.get("value", "unknown")


def _get_new_version(container: dict) -> str | None:
    """
    Return the available update version.
    Prefers updateKind.remoteValue, falls back to result.tag.
    Returns None if no update is available.
    """
    update_kind = container.get("updateKind", {}) or {}
    remote = update_kind.get("remoteValue")
    if remote:
        return remote
    result = container.get("result", {}) or {}
    tag = result.get("tag")
    if tag and tag != _get_current_version(container):
        return tag
    return None


def _get_image_created(container: dict) -> tuple[str | None, int | None]:
    """
    Return (formatted_date, days_since) based on image.created.
    This represents when the new image version was published.
    """
    image = container.get("image", {}) or {}
    created_str = image.get("created")
    if not created_str:
        return None, None
    try:
        created_str = created_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(created_str)
        days = (datetime.now(timezone.utc) - dt).days
        return dt.strftime("%Y-%m-%d %H:%M UTC"), days
    except (ValueError, TypeError):
        return None, None


def _build_controller_device(entry_id: str, instance_name: str) -> dict:
    """Build device info for the Controller device."""
    return {
        "identifiers": {(DOMAIN, f"{entry_id}_{CONTROLLER_DEVICE_SUFFIX}")},
        "name": f"WUD @ {instance_name}",
        "manufacturer": "What's Up Docker",
        "model": "Controller",
    }


def _build_container_device(entry_id: str, instance_name: str, container: dict) -> dict:
    """
    Build device info for a container or compose-project device.
    Containers sharing the same compose project are grouped under one device.
    Containers without a project fall under the Controller device.
    """
    project = _get_compose_project(container)
    controller_device_id = f"{entry_id}_{CONTROLLER_DEVICE_SUFFIX}"

    if project:
        return {
            "identifiers": {(DOMAIN, f"{entry_id}_{project}")},
            "name": f"{instance_name} – {project}",
            "manufacturer": "What's Up Docker",
            "model": "Docker Compose Project",
            "via_device": (DOMAIN, controller_device_id),
        }

    # No project — attach directly to the controller device
    return {
        "identifiers": {(DOMAIN, controller_device_id)},
        "name": f"WUD @ {instance_name}",
        "manufacturer": "What's Up Docker",
        "model": "Controller",
    }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WUD Monitor sensors from a config entry."""
    coordinator: WUDCoordinator = hass.data[DOMAIN][entry.entry_id]
    instance_name = entry.data[CONF_INSTANCE_NAME]

    entities: list[SensorEntity] = []

    # Controller-level sensors
    entities.append(WUDUpdateCountSensor(coordinator, entry, instance_name))
    entities.append(WUDTotalCountSensor(coordinator, entry, instance_name))
    entities.append(WUDLastPollSensor(coordinator, entry, instance_name))

    # Per-container sensors
    for container in coordinator.data or []:
        entities.append(WUDContainerSensor(coordinator, entry, instance_name, container))

    async_add_entities(entities)


class WUDControllerSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Controller-level sensors."""

    def __init__(
        self,
        coordinator: WUDCoordinator,
        entry: ConfigEntry,
        instance_name: str,
        sensor_key: str,
    ) -> None:
        """Initialize the controller sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._instance_name = instance_name
        self._attr_unique_id = f"wud_{entry.entry_id}_{sensor_key}"
        self._attr_device_info = _build_controller_device(entry.entry_id, instance_name)


class WUDUpdateCountSensor(WUDControllerSensorBase):
    """Sensor reporting the number of containers with available updates."""

    def __init__(self, coordinator, entry, instance_name) -> None:
        super().__init__(coordinator, entry, instance_name, "update_count")
        self._attr_name = f"WUD @ {instance_name} Containers with Updates"
        self._attr_icon = "mdi:update"
        self._attr_native_unit_of_measurement = "containers"

    @property
    def native_value(self) -> int:
        """Return the count of containers that have an update available."""
        if not self.coordinator.data:
            return 0
        return sum(1 for c in self.coordinator.data if c.get("updateAvailable", False))

    @property
    def extra_state_attributes(self) -> dict:
        """Return a list of containers that have an update available."""
        if not self.coordinator.data:
            return {}
        updates = [
            {
                "name": c.get("name"),
                "current_version": _get_current_version(c),
                "new_version": _get_new_version(c) or "–",
                "semver_diff": (c.get("updateKind") or {}).get("semverDiff"),
            }
            for c in self.coordinator.data
            if c.get("updateAvailable", False)
        ]
        return {"containers": updates}


class WUDTotalCountSensor(WUDControllerSensorBase):
    """Sensor reporting the total number of monitored containers."""

    def __init__(self, coordinator, entry, instance_name) -> None:
        super().__init__(coordinator, entry, instance_name, "total_count")
        self._attr_name = f"WUD @ {instance_name} Monitored Containers"
        self._attr_icon = "mdi:docker"
        self._attr_native_unit_of_measurement = "containers"

    @property
    def native_value(self) -> int:
        """Return the total number of containers returned by WUD."""
        return len(self.coordinator.data or [])


class WUDLastPollSensor(WUDControllerSensorBase):
    """Sensor reporting when HA last successfully polled WUD."""

    def __init__(self, coordinator, entry, instance_name) -> None:
        super().__init__(coordinator, entry, instance_name, "last_poll")
        self._attr_name = f"WUD @ {instance_name} Last Poll"
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> str | None:
        """Return the last poll time converted to the HA-configured local timezone."""
        last = getattr(self.coordinator, "last_poll_time", None)
        if last:
            local_dt = dt_util.as_local(last)
            return local_dt.strftime("%Y-%m-%d %H:%M:%S")
        return None


class WUDContainerSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a single WUD-monitored container."""

    def __init__(
        self,
        coordinator: WUDCoordinator,
        entry: ConfigEntry,
        instance_name: str,
        container: dict,
    ) -> None:
        """Initialize the container sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._instance_name = instance_name
        self._container_name = container["name"]
        self._container_watcher = container.get("watcher", "docker")

        self._attr_name = f"{container['name']} Update Available"

        # Stable unique_id — uses entry_id + watcher + name.
        # Container ID changes on every redeploy; watcher and name do not.
        self._attr_unique_id = (
            f"wud_{entry.entry_id}_{self._container_watcher}_{self._container_name}"
        )

        self._attr_device_info = _build_container_device(
            entry.entry_id, instance_name, container
        )

    def _get_container(self) -> dict | None:
        """Find this container's current data from the coordinator payload."""
        for c in self.coordinator.data or []:
            if c.get("name") == self._container_name and c.get("watcher") == self._container_watcher:
                return c
        return None

    @property
    def native_value(self) -> str:
        """Return 'Yes' if an update is available, otherwise 'No'."""
        container = self._get_container()
        if not container:
            return "unknown"
        return "Yes" if container.get("updateAvailable", False) else "No"

    @property
    def extra_state_attributes(self) -> dict:
        """Return detailed container attributes."""
        container = self._get_container()
        if not container:
            return {}

        image = container.get("image", {}) or {}
        registry = image.get("registry", {}) or {}
        update_kind = container.get("updateKind", {}) or {}

        current = _get_current_version(container)
        new = _get_new_version(container)
        available_since, days_available = _get_image_created(container)

        attrs: dict = {
            "container_id": container.get("id"),
            "image": image.get("name", "unknown"),
            "registry": registry.get("name", "unknown"),
            "current_version": current,
            "new_version": new or "–",
            "update_available": container.get("updateAvailable", False),
            "semver_diff": update_kind.get("semverDiff"),
            "status": container.get("status", "unknown"),
            "compose_project": _get_compose_project(container) or "–",
            "watcher": self._container_watcher,
        }

        # Only include date attributes when an update is actually available
        if container.get("updateAvailable") and available_since:
            attrs["available_since"] = available_since
            attrs["days_available"] = days_available

        return attrs
