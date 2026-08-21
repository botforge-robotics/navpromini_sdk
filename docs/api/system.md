# System

Identity and health. These two endpoints answer "what is this robot?" and "is it well?" —
the first two questions any integration needs settled.

### <span class="verb get">GET</span> `/system/info`

Identity, versions, and capabilities.

```bash
curl -s http://192.168.1.50:8090/api/v1/system/info
```

```json
{
  "robot": { "name": "navpromini", "serial": "46884ab7aa441027", "hostname": "navpromini" },
  "sdk_version": "1.0.0",
  "api_version": "v1",
  "ros_distro": "jazzy",
  "model": "NavProMini",
  "uptime_sec": 812.4,
  "capabilities": {
    "mapping": true,
    "navigation": true,
    "docking": true,
    "docking_method": "apriltag",
    "camera": true,
    "virtual_walls": false,
    "fixed_routes": false,
    "missions": false
  }
}
```

| Field | Meaning |
|---|---|
| `robot.name` | Configured robot name, shown on the robot's own display |
| `robot.serial` | CPU serial — unique per unit, stable across reinstalls |
| `robot.hostname` | Network hostname. Informational — address the robot by IP |
| `sdk_version` | Version of the SDK server |
| `api_version` | URL namespace in use (`v1`) |
| `uptime_sec` | How long the SDK server has been running — **not** robot uptime |
| `capabilities` | What this unit can do |

!!! tip "Branch on `capabilities`, not on failures"
    A `501` from a reserved endpoint and a temporarily broken subsystem look similar from
    the outside, and only one is worth retrying. Reading capabilities once at startup
    settles it.

`serial` is `null` when the CPU serial cannot be read; `name` falls back to the hostname.
This endpoint is deliberately the most defensive one in the SDK — it is the first thing
anyone calls when debugging a robot, so it answers even when parts of the robot stack are
not installed or not running.

---

### <span class="verb get">GET</span> `/system/health`

Per-subsystem freshness.

```bash
curl -s http://192.168.1.50:8090/api/v1/system/health
```

```json
{
  "healthy": true,
  "sources": {
    "odom":            { "ok": true, "age_sec": 0.07, "limit_sec": 2.0 },
    "battery":         { "ok": true, "age_sec": 3.44, "limit_sec": 5.0 },
    "imu":             { "ok": true, "age_sec": 0.07, "limit_sec": 2.0 },
    "lidar":           { "ok": true, "age_sec": 0.12, "limit_sec": 3.0 },
    "cpu_temperature": { "ok": true, "age_sec": 0.90, "limit_sec": 10.0 }
  },
  "cpu_temperature_c": 55.1,
  "disk": { "total_gb": 29.5, "free_gb": 18.2, "used_percent": 35.4 }
}
```

`healthy` is simply every source being `ok`. Each source reports:

- `age_sec` — seconds since that source last published, or `null` if it never has
- `limit_sec` — how stale it is allowed to get before `ok` goes false
- `ok` — `age_sec` is present and within `limit_sec`

The limits are generous multiples of each source's nominal rate, so a momentarily busy CPU
does not read as a dead sensor.

!!! info "Why per-source instead of one boolean"
    "The robot is unhealthy" gives an operator nothing to do. "Lidar last published 40
    seconds ago" points straight at the problem. The overall verdict is included for
    dashboards; the breakdown is for whoever has to fix it.

A source with `"age_sec": null` has **never** published in this session — usually a driver
that failed to start, which is a different problem from one that stopped.

The endpoint always returns <span class="status ok">200</span>, including when the robot
is unhealthy: the response body is the report, and a non-200 would make a monitoring system
unable to tell "unhealthy robot" from "unreachable robot".
