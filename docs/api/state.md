# State

Live telemetry. Every one of these is a cache read served from the robot's most recent
sensor message — none of them blocks, and none of them asks the hardware for anything.

## The shape

Every state response wraps the reading:

```json
{ "data": { ... }, "age_sec": 0.09 }
```

`age_sec` is how long ago the underlying sensor reported. Use it. A battery value 3 seconds
old is current; a pose 3 seconds old means localization has stopped. Only the caller knows
what tolerance the task needs, so the API reports the age rather than deciding for you.

A source that has never published returns <span class="status err">503 `no_data`</span>
instead of inventing zeros:

```json
{ "error": { "code": "no_data",
             "message": "No laser scan data received yet — is the robot fully started?",
             "detail": { "source": "scan" } } }
```

---

### <span class="verb get">GET</span> `/state/pose`

Current position and heading of the AMR.

#### Request
- **Method**: `GET`
- **Path**: `/state/pose`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "data": { "x": 0.99, "y": -0.364, "theta": 2.553, "frame": "map" },
  "age_sec": 0.09,
  "localized": true
}
```

| Field | Type | Description |
|---|---|---|
| `data.x`, `data.y` | `number` | Coordinates in metres relative to `frame` origin |
| `data.theta` | `number` | Heading in radians, counter-clockwise-positive (-π to +π) |
| `data.frame` | `string` | Coordinate frame: `map` (global) or `odom` (local drift) |
| `age_sec` | `number` | Seconds since the last localization or odometry update |
| `localized` | `boolean` | `true` only when `frame` is `map` and AMCL has converged |

!!! warning "Check `localized` before storing or comparing a pose"
    An `odom` pose is measured from wherever the robot last powered on. Storing one as a
    waypoint, or comparing it against a map coordinate, sends the robot somewhere else
    entirely.

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">503</span> | `no_data` | No pose published yet (e.g. during system startup) |

#### Example (cURL)

```bash
curl -s $ROBOT/state/pose
```

---

### <span class="verb get">GET</span> `/state/velocity`

Measured wheel odometry speed (actual physical movement, not commanded).

#### Request
- **Method**: `GET`
- **Path**: `/state/velocity`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "data": { "linear": 0.0, "angular": 0.0 },
  "age_sec": 0.07
}
```

| Field | Type | Description |
|---|---|---|
| `data.linear` | `number` | Forward/backward velocity in m/s (forward is positive) |
| `data.angular` | `number` | Rotational velocity in rad/s (counter-clockwise is positive) |
| `age_sec` | `number` | Seconds since the last odometry message |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">503</span> | `no_data` | Motor controller or wheel odometry driver not publishing |

#### Example (cURL)

```bash
curl -s $ROBOT/state/velocity
```

---

### <span class="verb get">GET</span> `/state/battery`

Battery charge state, voltage, current draw, and dock charging detection.

#### Request
- **Method**: `GET`
- **Path**: `/state/battery`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "data": {
    "percentage": 100.0,
    "voltage": 14.0,
    "current": 0.1,
    "temperature": 35.0,
    "status": "full",
    "charging": true
  },
  "age_sec": 3.45
}
```

| Field | Type | Description |
|---|---|---|
| `data.percentage` | `number` | State of charge (0.0 to 100.0%) |
| `data.voltage` | `number` | Battery pack voltage (V) |
| `data.current` | `number` | Battery current in Amperes (positive while charging) |
| `data.temperature` | `number` | Pack temperature in °C (or `null` if unavailable) |
| `data.status` | `string` | Battery status (`charging`, `discharging`, `not_charging`, `full`, `unknown`) |
| `data.charging` | `boolean` | **Ground truth for dock connection** (`true` whenever charge current flows) |
| `age_sec` | `number` | Seconds since the BMS last broadcast telemetry |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">503</span> | `no_data` | BMS telemetry not received from microcontroller |

#### Example (cURL)

```bash
curl -s $ROBOT/state/battery
```

---

### <span class="verb get">GET</span> `/state/imu`

Inertial measurement unit: orientation quaternion, angular velocity, and linear acceleration.

#### Request
- **Method**: `GET`
- **Path**: `/state/imu`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "data": {
    "orientation":         { "x": 0.0, "y": 0.0, "z": 0.958, "w": 0.287 },
    "angular_velocity":    { "x": 0.001, "y": -0.002, "z": 0.0 },
    "linear_acceleration": { "x": 0.04, "y": 0.01, "z": 9.79 }
  },
  "age_sec": 0.07
}
```

| Field | Type | Description |
|---|---|---|
| `data.orientation` | `object` | Raw orientation quaternion `{x, y, z, w}` |
| `data.angular_velocity` | `object` | Rotational rate `{x, y, z}` in rad/s |
| `data.linear_acceleration` | `object` | Linear acceleration `{x, y, z}` in m/s² (includes ~9.8 on Z for gravity) |
| `age_sec` | `number` | Seconds since the IMU published |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">503</span> | `no_data` | IMU sensor not streaming |

#### Example (cURL)

```bash
curl -s $ROBOT/state/imu
```

---

### <span class="verb get">GET</span> `/state/scan`

The latest 360° 2D LiDAR range scan.

#### Request
- **Method**: `GET`
- **Path**: `/state/scan`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "data": {
    "angle_min": -3.14159,
    "angle_max": 3.14159,
    "angle_increment": 0.008727,
    "range_min": 0.15,
    "range_max": 12.0,
    "count": 720,
    "ranges": [1.203, 1.198, null, 1.211, 2.45]
  },
  "age_sec": 0.12
}
```

| Field | Type | Description |
|---|---|---|
| `data.angle_min`, `angle_max` | `number` | Start and end scan angles in radians |
| `data.angle_increment` | `number` | Angular distance between consecutive beams |
| `data.range_min`, `range_max` | `number` | Valid sensor minimum and maximum range limits in metres |
| `data.count` | `integer` | Number of range measurements (typically ~720) |
| `data.ranges` | `array` | Range distance in metres (`null` indicates out of range or absorbed) |
| `age_sec` | `number` | Seconds since the LiDAR published this scan |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">503</span> | `no_data` | LiDAR node not running or not reporting points |

#### Example (cURL)

```bash
curl -s $ROBOT/state/scan
```

---

### <span class="verb get">GET</span> `/state/temperature`

Combined thermal monitor checking CPU and battery temperature in a single call.

#### Request
- **Method**: `GET`
- **Path**: `/state/temperature`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "cpu_c": 55.1,
  "battery_c": 35.0
}
```

| Field | Type | Description |
|---|---|---|
| `cpu_c` | `number` | Host processor temperature in degrees Celsius (or `null`) |
| `battery_c` | `number` | Battery pack temperature in degrees Celsius (or `null`) |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">401</span> | `unauthorized` | Missing or invalid authentication token |

#### Example (cURL)

```bash
curl -s $ROBOT/state/temperature
```
