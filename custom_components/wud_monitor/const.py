"""Constants for the WUD Monitor integration."""

DOMAIN = "wud_monitor"

# Config entry keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_INSTANCE_NAME = "instance_name"
CONF_POLL_INTERVAL = "poll_interval"

# Defaults
DEFAULT_PORT = 3000
DEFAULT_POLL_INTERVAL = 15  # minutes
DEFAULT_INSTANCE_NAME = "WUD"

# API endpoints
API_CONTAINERS = "/api/containers"
API_CONTAINERS_WATCH = "/api/containers/watch"
API_CONTAINER_WATCH = "/api/containers/{container_id}/watch"

# Device identifiers
CONTROLLER_DEVICE_SUFFIX = "controller"
