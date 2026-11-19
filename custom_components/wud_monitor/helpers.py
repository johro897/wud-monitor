"""Shared helpers for the WUD Monitor integration."""

import re

_VERSION_SEPARATOR = re.compile(r"[.\-+]")


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


def _strip_v(value: str) -> str:
    """Drop a leading ``v``/``V`` so ``v3.2.0`` compares equal to ``3.2.0``."""
    return value[1:] if value[:1] in ("v", "V") else value


def get_current_version(container: dict) -> str:
    """Return the version the container is currently running.

    The ``org.opencontainers.image.version`` label can be more precise than the
    tag (``2026.2`` -> ``2026.2.4``), but images inherit it from their base
    image, so an image built on Ubuntu may carry ``24.04`` without being that
    version. The label is therefore only trusted when it refines the tag, or
    when the tag carries no version of its own (``latest``); otherwise the tag
    is used.
    """
    labels = container.get("labels", {}) or {}
    tag_info = (container.get("image", {}) or {}).get("tag", {}) or {}
    tag = tag_info.get("value")
    oci_version = labels.get("org.opencontainers.image.version")

    if not tag:
        return oci_version or "unknown"
    if not oci_version:
        return tag
    if not tag_info.get("semver"):
        return oci_version

    tag_core, label_core = _strip_v(tag), _strip_v(oci_version)
    if label_core == tag_core or (
        label_core.startswith(tag_core)
        and _VERSION_SEPARATOR.match(label_core[len(tag_core):])
    ):
        return oci_version
    return tag
