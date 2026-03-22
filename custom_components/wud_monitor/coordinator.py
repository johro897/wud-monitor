"""DataUpdateCoordinator for WUD Monitor."""

import logging
from datetime import timedelta

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_CONTAINERS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class WUDCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches all container data from WUD in a single API call."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, poll_interval: int) -> None:
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        self._base_url = f"http://{host}:{port}"

        self.last_poll_time: object = None  # Set on each successful poll
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=poll_interval),
        )

    async def _async_update_data(self) -> list[dict]:
        """Fetch container data from WUD API. Called by the coordinator on each poll."""
        from datetime import datetime, timezone
        url = f"{self._base_url}{API_CONTAINERS}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"WUD API returned HTTP {response.status}")
                    data = await response.json()
                    # API returns either a list or a dict with an "items" key
                    result = data if isinstance(data, list) else data.get("items", [])
                    # Store poll time only on success
                    self.last_poll_time = datetime.now(timezone.utc)
                    return result
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with WUD at {self._base_url}: {err}") from err

    async def async_trigger_scan_all(self) -> bool:
        """Trigger a scan of all containers via POST /api/containers/watch."""
        from .const import API_CONTAINERS_WATCH
        url = f"{self._base_url}{API_CONTAINERS_WATCH}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    return response.status in (200, 202, 204)
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to trigger WUD scan all: %s", err)
            return False

    async def async_trigger_scan_container(self, container_id: str) -> bool:
        """Trigger a scan for a specific container via GET /api/containers/{id}/watch."""
        from .const import API_CONTAINER_WATCH
        url = f"{self._base_url}{API_CONTAINER_WATCH.format(container_id=container_id)}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    return response.status in (200, 202, 204)
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to trigger WUD scan for container %s: %s", container_id, err)
            return False
