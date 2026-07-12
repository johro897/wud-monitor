"""Constants for the WUD Monitor integration."""

DOMAIN = "wud_monitor"

# Config entry keys
CONF_HOST          = "host"
CONF_PORT          = "port"
CONF_INSTANCE_NAME = "instance_name"
CONF_POLL_INTERVAL = "poll_interval"

# Auth
CONF_AUTH_METHOD = "auth_method"
CONF_USERNAME    = "username"
CONF_PASSWORD    = "password"
CONF_API_KEY     = "api_key"

AUTH_METHOD_NONE    = "none"
AUTH_METHOD_BASIC   = "basic"
AUTH_METHOD_API_KEY = "api_key"

# Defaults
DEFAULT_PORT          = 3000
DEFAULT_POLL_INTERVAL = 15  # minutes
DEFAULT_INSTANCE_NAME = "WUD"

# API endpoints
API_CONTAINERS       = "/api/containers"
API_CONTAINERS_WATCH = "/api/containers/watch"
API_CONTAINER_WATCH  = "/api/containers/{container_id}/watch"

# Device identifiers
CONTROLLER_DEVICE_SUFFIX = "controller"
