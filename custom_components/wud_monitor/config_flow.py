"""Config flow for WUD Monitor."""
import logging
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from .const import (
    AUTH_METHOD_NONE,
    AUTH_METHOD_BASIC,
    AUTH_METHOD_API_KEY,
    CONF_AUTH_METHOD,
    CONF_API_KEY,
    CONF_HOST,
    CONF_INSTANCE_NAME,
    CONF_PASSWORD,
    CONF_POLL_INTERVAL,
    CONF_PORT,
    CONF_USERNAME,
    DEFAULT_INSTANCE_NAME,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

AUTH_METHODS = [AUTH_METHOD_NONE, AUTH_METHOD_BASIC, AUTH_METHOD_API_KEY]


def _build_connection_schema(defaults: dict) -> vol.Schema:
    """Schema for step 1 — host, port, name, poll interval, auth method."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(
                CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)
            ): vol.All(int, vol.Range(min=1, max=65535)),
            vol.Required(
                CONF_INSTANCE_NAME,
                default=defaults.get(CONF_INSTANCE_NAME, DEFAULT_INSTANCE_NAME),
            ): str,
            vol.Required(
                CONF_POLL_INTERVAL,
                default=defaults.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
            ): vol.All(int, vol.Range(min=1, max=1440)),
            vol.Required(
                CONF_AUTH_METHOD,
                default=defaults.get(CONF_AUTH_METHOD, AUTH_METHOD_NONE),
            ): vol.In(AUTH_METHODS),
        }
    )


def _build_basic_auth_schema(defaults: dict) -> vol.Schema:
    """Schema for step 2a — Basic Auth credentials."""
    return vol.Schema(
        {
            vol.Required(
                CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")
            ): str,
            vol.Required(
                CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        }
    )


def _build_api_key_schema(defaults: dict) -> vol.Schema:
    """Schema for step 2b — API key."""
    return vol.Schema(
        {
            vol.Required(
                CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        }
    )


def _build_auth(data: dict) -> aiohttp.BasicAuth | None:
    """Build aiohttp auth object from config data."""
    method = data.get(CONF_AUTH_METHOD, AUTH_METHOD_NONE)
    if method == AUTH_METHOD_BASIC:
        return aiohttp.BasicAuth(data[CONF_USERNAME], data[CONF_PASSWORD])
    return None


def _build_headers(data: dict) -> dict:
    """Build request headers from config data."""
    method = data.get(CONF_AUTH_METHOD, AUTH_METHOD_NONE)
    if method == AUTH_METHOD_API_KEY:
        return {"Authorization": f"Bearer {data[CONF_API_KEY]}"}
    return {}


async def _test_connection(data: dict) -> str:
    """Test that we can reach the WUD API with the given config.

    Returns "ok", "invalid_auth" (WUD reachable but rejected the
    credentials), or "cannot_connect" (host unreachable, timeout, or any
    other non-200/401 response).
    """
    host = data[CONF_HOST]
    port = data[CONF_PORT]
    url = f"http://{host}:{port}/api/containers"
    auth = _build_auth(data)
    headers = _build_headers(data)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                auth=auth,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    return "ok"
                if response.status == 401:
                    return "invalid_auth"
                return "cannot_connect"
    except Exception:  # noqa: BLE001
        return "cannot_connect"


class WUDMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._data: dict = {}

    async def async_step_user(self, user_input: dict | None = None):
        """Step 1 — connection details and auth method selection."""
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()
            self._data.update(user_input)

            # Route to the correct auth step
            auth_method = user_input[CONF_AUTH_METHOD]
            if auth_method == AUTH_METHOD_BASIC:
                return await self.async_step_basic_auth()
            if auth_method == AUTH_METHOD_API_KEY:
                return await self.async_step_api_key()

            # No auth — test and create immediately
            return await self._async_test_and_create()

        return self.async_show_form(
            step_id="user",
            data_schema=_build_connection_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_basic_auth(self, user_input: dict | None = None):
        """Step 2a — Basic Auth credentials."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self._async_test_and_create(errors)

        return self.async_show_form(
            step_id="basic_auth",
            data_schema=_build_basic_auth_schema(self._data),
            errors=errors,
        )

    async def async_step_api_key(self, user_input: dict | None = None):
        """Step 2b — API key."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self._async_test_and_create(errors)

        return self.async_show_form(
            step_id="api_key",
            data_schema=_build_api_key_schema(self._data),
            errors=errors,
        )

    async def _async_test_and_create(self, errors: dict | None = None):
        """Test the connection and create the config entry if successful."""
        if errors is None:
            errors = {}

        result = await _test_connection(self._data)
        if result != "ok":
            errors["base"] = "invalid_auth" if result == "invalid_auth" else "cannot_connect"
            # Return to the auth step so the user can correct credentials
            auth_method = self._data.get(CONF_AUTH_METHOD, AUTH_METHOD_NONE)
            if auth_method == AUTH_METHOD_BASIC:
                return self.async_show_form(
                    step_id="basic_auth",
                    data_schema=_build_basic_auth_schema(self._data),
                    errors=errors,
                )
            if auth_method == AUTH_METHOD_API_KEY:
                return self.async_show_form(
                    step_id="api_key",
                    data_schema=_build_api_key_schema(self._data),
                    errors=errors,
                )
            # No auth — back to step 1
            return self.async_show_form(
                step_id="user",
                data_schema=_build_connection_schema(self._data),
                errors=errors,
            )

        return self.async_create_entry(
            title=self._data[CONF_INSTANCE_NAME],
            data=self._data,
        )

    async def async_step_reauth(self, entry_data: dict):
        """Handle reauthentication triggered by ConfigEntryAuthFailed (e.g. a rotated token or changed password)."""
        self._data = dict(entry_data)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict | None = None):
        """Ask for updated credentials for the existing entry and verify them."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            result = await _test_connection(self._data)
            if result == "ok":
                reauth_entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                self.hass.config_entries.async_update_entry(
                    reauth_entry, data=self._data
                )
                await self.hass.config_entries.async_reload(reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            errors["base"] = "invalid_auth" if result == "invalid_auth" else "cannot_connect"

        auth_method = self._data.get(CONF_AUTH_METHOD, AUTH_METHOD_NONE)
        if auth_method == AUTH_METHOD_BASIC:
            schema = _build_basic_auth_schema(self._data)
        elif auth_method == AUTH_METHOD_API_KEY:
            schema = _build_api_key_schema(self._data)
        else:
            # No auth was configured but WUD started rejecting requests —
            # let the user pick/enable an auth method again.
            schema = _build_connection_schema(self._data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return WUDMonitorOptionsFlow()


class WUDMonitorOptionsFlow(config_entries.OptionsFlow):
    """Handle options updates — supports changing auth method."""

    def __init__(self) -> None:
        """Initialise the options flow."""
        self._data: dict = {}

    async def async_step_init(self, user_input: dict | None = None):
        """Step 1 — connection details and auth method selection."""
        errors = {}

        if user_input is not None:
            self._data = {**self.config_entry.data, **user_input}
            auth_method = user_input[CONF_AUTH_METHOD]
            if auth_method == AUTH_METHOD_BASIC:
                return await self.async_step_basic_auth()
            if auth_method == AUTH_METHOD_API_KEY:
                return await self.async_step_api_key()
            return await self._async_test_and_save()

        return self.async_show_form(
            step_id="init",
            data_schema=_build_connection_schema(self.config_entry.data),
            errors=errors,
        )

    async def async_step_basic_auth(self, user_input: dict | None = None):
        """Step 2a — Basic Auth credentials."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self._async_test_and_save(errors)

        return self.async_show_form(
            step_id="basic_auth",
            data_schema=_build_basic_auth_schema(self._data),
            errors=errors,
        )

    async def async_step_api_key(self, user_input: dict | None = None):
        """Step 2b — API key."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self._async_test_and_save(errors)

        return self.async_show_form(
            step_id="api_key",
            data_schema=_build_api_key_schema(self._data),
            errors=errors,
        )

    async def _async_test_and_save(self, errors: dict | None = None):
        """Test the connection and save if successful."""
        if errors is None:
            errors = {}

        result = await _test_connection(self._data)
        if result != "ok":
            errors["base"] = "invalid_auth" if result == "invalid_auth" else "cannot_connect"
            auth_method = self._data.get(CONF_AUTH_METHOD, AUTH_METHOD_NONE)
            if auth_method == AUTH_METHOD_BASIC:
                return self.async_show_form(
                    step_id="basic_auth",
                    data_schema=_build_basic_auth_schema(self._data),
                    errors=errors,
                )
            if auth_method == AUTH_METHOD_API_KEY:
                return self.async_show_form(
                    step_id="api_key",
                    data_schema=_build_api_key_schema(self._data),
                    errors=errors,
                )
            return self.async_show_form(
                step_id="init",
                data_schema=_build_connection_schema(self._data),
                errors=errors,
            )

        self.hass.config_entries.async_update_entry(
            self.config_entry, data=self._data
        )
        return self.async_create_entry(title="", data={})
