# WUD Monitor

A Home Assistant integration for [What's Up Docker (WUD)](https://github.com/getwud/wud) that tracks container update availability and exposes controls directly in Home Assistant.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/johro897/wud-monitor)

---

## Features

- **Per-container sensors** — update status, current version, new version, days available
- **Controller sensors** — total containers monitored, containers with updates, last poll time
- **Force scan buttons** — trigger WUD to re-check updates for all containers, a specific compose project, or a single container
- **Compose project grouping** — containers sharing a Docker Compose project are grouped under one HA device
- **Authentication support** — connect to WUD instances protected by Basic Auth or API Key
- **Re-deploy safe** — sensor identity is based on container name and watcher, not the Docker container ID which changes on every redeploy
- **Configurable polling** — set how often HA polls WUD (default: 15 minutes)
- **Multi-instance support** — add multiple WUD instances, each gets its own devices and sensors

---

## Requirements

- Home Assistant 2024.1 or newer
- [HACS](https://hacs.xyz/) installed
- A running [What's Up Docker](https://github.com/getwud/wud) instance (tested with WUD 8.2+)

### WUD container labels

For WUD to monitor a container, add `wud.watch: "true"` to its `docker-compose.yml`:

```yaml
labels:
  - "wud.watch=true"
```

To stay on the same version track and avoid pre-releases or variant tags, add `wud.tag.include`:

```yaml
labels:
  - "wud.watch=true"
  # SemVer: stay on 2.0.x only
  - "wud.tag.include=^2\\.0\\.\\d+$"

  # CalVer: stay on same year.month.patch — no dev/rc builds
  - "wud.tag.include=^20[0-9]{2}\\.[0-9]+\\.[0-9]+$"

  # Block pre-releases and variant tags for any versioning scheme
  - "wud.tag.exclude=^.*(dev|alpha|beta|rc|alpine|slim|snapshot).*$"
```

To get a `release_notes` link on the container's sensor (see below), add `wud.link.template` with the version placed via `${major}`/`${minor}`/`${patch}`/`${original}`/`${transformed}`/`${prerelease}`:

```yaml
labels:
  - "wud.watch=true"
  - "wud.link.template=https://github.com/getwud/wud/releases/tag/${original}"
```

Without this label WUD has no changelog URL to give, so `release_notes` simply won't be present on the sensor — nothing else is affected.

---

## Installation

### Via HACS (recommended)

1. In HACS, go to **Integrations → ⋮ → Custom repositories**
2. Paste `https://github.com/johro897/wud-monitor` and choose **Integration**
3. Click **Add**, then find **WUD Monitor** and install it
4. Restart Home Assistant

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=johro897&repository=wud-monitor&category=integration)

### Manual installation

1. Copy the `custom_components/wud_monitor` folder to your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Configuration

Go to **Settings → Devices & Services → Add Integration** and search for **WUD Monitor**.

### Step 1 — Connection

| Field | Description | Default |
|---|---|---|
| **Host** | IP address or hostname of your WUD instance | — |
| **Port** | WUD web UI port | `3000` |
| **Instance name** | Friendly name shown as the Controller device in HA | `WUD` |
| **Poll interval** | How often HA fetches data from WUD (minutes) | `15` |
| **Authentication method** | How to authenticate with the WUD API | `None` |

### Step 2 — Authentication (if required)

If your WUD instance has authentication enabled, select the matching method in step 1 and enter credentials in step 2.

**None** — no credentials required. Skip step 2 entirely.

**Basic Auth** — enter the username and password configured in WUD:

```yaml
# Example WUD environment variable for Basic Auth
WUD_AUTH_BASIC_JOHNDOE_USER: johndoe
WUD_AUTH_BASIC_JOHNDOE_PASSWORD: secret
```

**API Key** — enter the API key configured in WUD. It is sent as a `Bearer` token in the `Authorization` header:

```yaml
# Example WUD environment variable for API Key
WUD_AUTH_BEARER_MYTOKEN_TOKEN: mysecrettoken
```

Settings can be changed later via the integration's **Configure** button, including switching authentication method.

---

## Devices and entities

### Controller device (`WUD @ {instance_name}`)

| Entity | Type | Description |
|---|---|---|
| Containers with Updates | Sensor | Number of containers that have an update available |
| Monitored Containers | Sensor | Total number of containers WUD is watching |
| Last Poll | Sensor | When HA last successfully fetched data from WUD |
| Force Scan All | Button | Triggers `POST /api/containers/watch` to re-check all containers |
| Refresh States | Button | Re-fetches current container data (`GET /api/containers`) without asking WUD to check for updates — useful right after you've made a change in WUD itself |

### Compose project device (`{instance_name} – {project}`)

One device per Docker Compose project. Linked to the Controller device via `via_device`.

| Entity | Type | Description |
|---|---|---|
| {container} Update Available | Sensor | Per-container update status |
| Force Scan | Button | Scans each container in the project individually |

### Per-container sensor attributes

| Attribute | Description |
|---|---|
| `current_version` | Currently running version |
| `new_version` | Available update version (`–` if none) |
| `available_since` | When the new image was published (UTC) — only shown when update is available |
| `days_available` | Days since the new version became available — only shown when update is available |
| `release_notes` | Browsable link to the release notes / changelog for the available update — only shown when an update is available **and** the container has a `wud.link.template` label configured in WUD (see [WUD's watcher docs](https://github.com/getwud/wud/blob/main/docs/configuration/watchers/README.md)) |
| `error` | The error WUD itself reported for this container (e.g. registry rate limit, registry auth failure) — only shown when WUD actually reports one |
| `semver_diff` | Severity: `patch`, `minor`, or `major` |
| `image` | Full image name (e.g. `esphome/esphome`) |
| `registry` | Registry name (e.g. `ghcr.public`, `hub.public`) |
| `compose_project` | Docker Compose project name |
| `status` | Container runtime status (e.g. `running`) |
| `watcher` | WUD watcher name (e.g. `docker`) |

---

## Troubleshooting

**Integration fails to connect**
Verify that the WUD API is reachable from Home Assistant:
```
http://<wud_host>:<wud_port>/api/containers
```
This should return a JSON array of your monitored containers. If you get a `401 Unauthorized` response, your WUD instance requires authentication — reconfigure the integration and select the correct auth method.

**Authentication fails**
- For Basic Auth: verify the username and password match the `WUD_AUTH_BASIC_*` environment variables in your WUD container
- For API Key: verify the token matches `WUD_AUTH_BEARER_*_TOKEN` and that it is sent as a `Bearer` token
- You can test from the command line: `curl -H "Authorization: Bearer <token>" http://<wud_host>:<wud_port>/api/containers`

**Duplicate sensors after container redeploy**
This integration uses `watcher + name` as the stable entity identity, not the Docker container ID. If you are upgrading from an older version that used container ID, delete the old `unavailable` entities manually under **Settings → Devices & Services**.

**Sensors not updating**
Check the poll interval in the integration settings. You can also press the **Force Scan All** button to trigger an immediate refresh.

---

## Changelog

### 2.4
**Security hardening** — [#7](https://github.com/johro897/wud-monitor/issues/7)
- The Basic Auth password and API key fields in the config flow are now masked (password-style input) instead of shown in plain text while typing
- A `401 Unauthorized` response from WUD now triggers Home Assistant's standard reauthentication flow (a repair notification prompting you to re-enter credentials) instead of just marking entities unavailable with a generic error
- The config flow now distinguishes "WUD rejected the credentials" from "couldn't reach WUD at all," instead of showing the same generic message for both

**Performance & correctness** — [#8](https://github.com/johro897/wud-monitor/issues/8)
- Container lookups (per-container sensor, per-container/project Force Scan buttons) now use a single cached `{(name, watcher): container}` dict built once per poll, instead of each entity scanning the full container list on every property access
- A container sensor whose container has disappeared from WUD (renamed/removed) now correctly shows as `unavailable` instead of the state `unknown`
- The per-container Force Scan button no longer silently falls back to a stale container ID from setup time when the container can't be resolved live — it now logs an error and does nothing, instead of sending a request that would just 404 against WUD

### 2.2
**Fixes** — requested in [#3](https://github.com/johro897/wud-monitor/issues/3)
- Single-container scan now uses `POST` instead of `GET` — WUD only registers `POST /:id/watch`, so the per-container and compose-project Force Scan buttons were not actually triggering a scan
- Compose-project Force Scan now re-resolves each container's current ID at press time instead of reusing IDs captured at entity setup, which went stale after any redeploy

**Release notes link** — [#4](https://github.com/johro897/wud-monitor/issues/4)
- New `release_notes` attribute on the per-container sensor — a browsable link to the update's changelog, read from WUD's `result.link` (populated when the container has a `wud.link.template` label configured in WUD)

**Other additions** — [#5](https://github.com/johro897/wud-monitor/issues/5)
- New `error` attribute — surfaces WUD's own reported error for a container (registry rate limit, auth failure, etc.) directly on the sensor
- New **Refresh States** button — re-fetches container data without asking WUD to check for updates
- Request timeouts increased from 10s to 15s for more headroom on slower WUD instances

### 2.1
Adds authentication support (Basic Auth and API Key) via a multi-step config flow, so WUD instances that require credentials are no longer rejected with a `401`. No breaking changes for existing installations.

### 2.0
Official HACS release.

### 1.0
First real release.

## Contributions

Contributions are welcome! Open an issue or pull request on [GitHub](https://github.com/johro897/wud-monitor).
