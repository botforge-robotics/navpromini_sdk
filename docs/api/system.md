# System

Identity and health. These two endpoints answer "what is this robot?" and "is it well?" —
the first two questions any integration needs settled.

### <span class="verb get">GET</span> `/system/info`

Identity, software versions, and hardware capabilities.

#### Request
- **Method**: `GET`
- **Path**: `/system/info`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

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
    "missions": true
  }
}
```

| Field | Type | Description |
|---|---|---|
| `robot.name` | `string` | Configured robot name, shown on the robot's own display |
| `robot.serial` | `string` | CPU serial — unique per unit, stable across reinstalls |
| `robot.hostname` | `string` | Network hostname. Informational — address the robot by IP |
| `sdk_version` | `string` | Version of the SDK server |
| `api_version` | `string` | URL namespace in use (`v1`) |
| `uptime_sec` | `number` | How long the SDK server has been running — **not** robot uptime |
| `capabilities` | `object` | Map of enabled subsystem features and behaviors |

!!! tip "Branch on `capabilities`, not on failures"
    A `501` from a reserved endpoint and a temporarily broken subsystem look similar from
    the outside, and only one is worth retrying. Reading capabilities once at startup
    settles it.

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">401</span> | `unauthorized` | Token authentication enabled on robot and header missing or incorrect |

#### Example (cURL)

```bash
curl -s $ROBOT/system/info
```

---

### <span class="verb get">GET</span> `/system/health`

Per-subsystem freshness and hardware monitoring.

#### Request
- **Method**: `GET`
- **Path**: `/system/health`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

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

| Field | Type | Description |
|---|---|---|
| `healthy` | `boolean` | `true` if every critical sensor and driver source is publishing within its stale limit |
| `sources` | `object` | Per-sensor breakdown with `ok`, `age_sec`, and maximum allowed `limit_sec` |
| `cpu_temperature_c` | `number` | Host processor temperature in degrees Celsius |
| `disk` | `object` | Storage breakdown with `total_gb`, `free_gb`, and `used_percent` |

Each source reports:
- `age_sec` — seconds since that source last published, or `null` if it never has
- `limit_sec` — how stale it is allowed to get before `ok` goes false
- `ok` — `age_sec` is present and within `limit_sec`

A source with `"age_sec": null` has **never** published in this session — usually a driver that failed to start.

The endpoint always returns <span class="status ok">200</span>, including when the robot is unhealthy: the response body is the report itself.

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">401</span> | `unauthorized` | Token authentication enabled on robot and header missing or incorrect |

#### Example (cURL)

```bash
curl -s $ROBOT/system/health
```
