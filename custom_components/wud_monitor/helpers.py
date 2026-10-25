"""Shared helpers for the WUD Monitor integration."""


def build_base_url(host: str, port: int, use_ssl: bool) -> str:
    """Return the WUD base URL for the given connection settings."""
    scheme = "https" if use_ssl else "http"
    return f"{scheme}://{host}:{port}"


async def async_read_error(response) -> str:
    """Return WUD's own error text for a failed response.

    WUD 9 answers ``{"error": "<Type>", "message": "<Details>"}``; older
    versions and some routes use a flat ``{"error": "..."}`` or plain text.
    Never raises — an unreadable body just yields an empty string.
    """
    try:
        data = await response.json(content_type=None)
    except Exception:  # noqa: BLE001
        try:
            return (await response.text()).strip()[:200]
        except Exception:  # noqa: BLE001
            return ""
    if isinstance(data, dict):
        return str(data.get("message") or data.get("error") or "")[:200]
    return ""
