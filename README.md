# WUD Monitor

A Home Assistant integration for [What's Up Docker (WUD)](https://github.com/getwud/wud) that tracks container update availability and exposes controls directly in Home Assistant.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/johro897/wud-monitor)

---

## Features

- **Per-container sensors** — update status, current version, new version, days available
- **Controller sensors** — total containers monitored, containers with updates, last poll time
- **Force scan buttons** — trigger WUD to re-check updates for all containers, a specific compose project, or a single container
- **Compose project grouping** — containers sharing a Docker Compose project are grouped under one HA device
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

| Field | Description | Default |
|---|---|---|
| **Host** | IP address or hostname of your WUD instance | — |
| **Port** | WUD web UI port | `3000` |
| **Instance name** | Friendly name shown as the Controller device in HA | `WUD` |
| **Poll interval** | How often HA fetches data from WUD (minutes) | `15` |

Settings can be changed later via the integration's **Configure** button.

---

## Devices and entities

### Controller device (`WUD @ {instance_name}`)

| Entity | Type | Description |
|---|---|---|
| Containers with Updates | Sensor | Number of containers that have an update available |
| Monitored Containers | Sensor | Total number of containers WUD is watching |
| Last Poll | Sensor | When HA last successfully fetched data from WUD |
| Force Scan All | Button | Triggers `POST /api/containers/watch` to re-check all containers |

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
| `semver_diff` | Severity: `patch`, `minor`, or `major` |
| `image` | Full image name (e.g. `esphome/esphome`) |
| `registry` | Registry name (e.g. `ghcr.public`, `hub.public`) |
| `compose_project` | Docker Compose project name |
| `status` | Container runtime status (e.g. `running`) |
| `watcher` | WUD watcher name (e.g. `docker`) |

---

## Troubleshooting

**Integration fails to connect**
Verify that the WUD API is reachable:
```
http://<wud_host>:<wud_port>/api/containers
```
This should return a JSON array of your monitored containers.

**Duplicate sensors after container redeploy**
This integration uses `watcher + name` as the stable entity identity, not the Docker container ID. If you are upgrading from an older version that used container ID, delete the old `unavailable` entities manually under **Settings → Devices & Services**.

**Sensors not updating**
Check the poll interval in the integration settings. You can also press the **Force Scan All** button to trigger an immediate refresh.

---

## Contributions

Contributions are welcome! Open an issue or pull request on [GitHub](https://github.com/johro897/wud-monitor).
