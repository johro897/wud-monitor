"""DataUpdateCoordinator for WUD Monitor."""
import logging
from datetime import timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_CONTAINERS,
    AUTH_METHOD_BASIC,
    AUTH_METHOD_API_KEY,
    CONF_AUTH_METHOD,
    CONF_API_KEY,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class WUDCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches all container data from WUD in a single API call."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        poll_interval: int,
        auth_config: dict | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        self._base_url = f"http://{host}:{port}"
        self._auth_config = auth_config or {}
        self.last_poll_time: object = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=poll_interval),
        )

    # ── Auth helpers ──────────────────────────────────────────────────────────

    def _get_auth(self) -> aiohttp.BasicAuth | None:
        """Return aiohttp BasicAuth if Basic Auth is configured."""
        if self._auth_config.get(CONF_AUTH_METHOD) == AUTH_METHOD_BASIC:
            return aiohttp.BasicAuth(
                self._auth_config[CONF_USERNAME],
                self._auth_config[CONF_PASSWORD],
            )
        return None

    def _get_headers(self) -> dict:
        """Return Authorization header if API Key is configured."""
        if self._auth_config.get(CONF_AUTH_METHOD) == AUTH_METHOD_API_KEY:
            return {"Authorization": f"Bearer {self._auth_config[CONF_API_KEY]}"}
        return {}

    def _session_kwargs(self) -> dict:
        """Return kwargs to pass to every aiohttp request."""
        return {
            "auth": self._get_auth(),
            "headers": self._get_headers(),
        }

    # ── API calls ─────────────────────────────────────────────────────────────

    async def _async_update_data(self) -> list[dict]:
        """Fetch container data from WUD API. Called by the coordinator on each poll."""
        from datetime import datetime, timezone

        url = f"{self._base_url}{API_CONTAINERS}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    **self._session_kwargs(),
                ) as response:
                    if response.status == 401:
                        raise UpdateFailed(
                            "WUD API returned 401 Unauthorized — check authentication settings"
                        )
                    if response.status != 200:
                        raise UpdateFailed(f"WUD API returned HTTP {response.status}")
                    data = await response.json()
                    result = data if isinstance(data, list) else data.get("items", [])
                    self.last_poll_time = datetime.now(timezone.utc)
                    return result
        except aiohttp.ClientError as err:
            raise UpdateFailed(
                f"Error communicating with WUD at {self._base_url}: {err}"
            ) from err

    async def async_trigger_scan_all(self) -> bool:
        """Trigger a scan of all containers via POST /api/containers/watch."""
        from .const import API_CONTAINERS_WATCH

        url = f"{self._base_url}{API_CONTAINERS_WATCH}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    **self._session_kwargs(),
                ) as response:
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
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    **self._session_kwargs(),
                ) as response:
                    return response.status in (200, 202, 204)
        except aiohttp.ClientError as err:
            _LOGGER.error(
                "Failed to trigger WUD scan for container %s: %s", container_id, err
            )
            return False
