"""Shared helpers for the WUD Monitor integration."""


def build_base_url(host: str, port: int, use_ssl: bool) -> str:
    """Return the WUD base URL for the given connection settings."""
    scheme = "https" if use_ssl else "http"
    return f"{scheme}://{host}:{port}"
