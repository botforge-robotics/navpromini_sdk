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

Where the robot is.

```json
{ "data": { "x": 0.99, "y": -0.364, "theta": 2.553, "frame": "odom" },
  "age_sec": 0.09,
  "localized": false }
```

| Field | Meaning |
|---|---|
| `x`, `y` | Metres, in `frame` |
| `theta` | Heading in radians, counter-clockwise-positive |
| `frame` | `map` or `odom` — see below |
| `localized` | `true` only when `frame` is `map` |

The endpoint prefers the `map` frame and falls back to `odom` when AMCL is not running
(idle or mapping mode), saying which it used.

!!! warning "Check `localized` before storing or comparing a pose"
    An `odom` pose is measured from wherever the robot last powered on. Storing one as a
    waypoint, or comparing it against a map coordinate, sends the robot somewhere else
    entirely — and it will go there confidently. Labelling an odom pose "map" would be a
    genuinely dangerous lie, so the API refuses to.

---

### <span class="verb get">GET</span> `/state/velocity`

Measured — not commanded — motion, from wheel odometry.

```json
{ "data": { "linear": 0.0, "angular": 0.0 }, "age_sec": 0.07 }
```

`linear` in m/s, forward positive. `angular` in rad/s, counter-clockwise positive.

---

### <span class="verb get">GET</span> `/state/battery`

```json
{ "data": { "percentage": 100.0, "voltage": 14.0, "current": 0.1,
            "temperature": 35.0, "status": "full", "charging": true },
  "age_sec": 3.45 }
```

| Field | Meaning |
|---|---|
| `percentage` | 0–100 |
| `voltage` | Volts |
| `current` | Amps. Positive while charging |
| `temperature` | Pack temperature in °C, or `null` if not reported |
| `status` | `unknown`, `charging`, `discharging`, `not_charging`, `full` |
| `charging` | `true` when `status` is `charging` or `full` |

**`charging` is the ground truth for being on the dock.** It is true whenever current is
flowing, regardless of what the docking controller believes — including when someone pushed
the robot onto its dock by hand.

`status: "full"` counts as charging because a robot sitting on a full charge is still
physically connected, and callers asking "is it on the dock?" mean exactly that.

A `detail` object appears when the battery controller publishes extended diagnostics
(cell voltages, cycle count). Its contents vary by firmware — treat it as informational.

---

### <span class="verb get">GET</span> `/state/imu`

```json
{ "data": {
    "orientation":         { "x": 0.0, "y": 0.0, "z": 0.958, "w": 0.287 },
    "angular_velocity":    { "x": 0.001, "y": -0.002, "z": 0.0 },
    "linear_acceleration": { "x": 0.04, "y": 0.01, "z": 9.79 } },
  "age_sec": 0.07 }
```

This is the only place a quaternion appears, because it is the raw sensor value and
converting it would discard roll and pitch. For heading, use `/state/pose`.

Angular velocity is rad/s; linear acceleration is m/s² and **includes gravity** — roughly
9.8 on `z` when the robot is level and still.

---

### <span class="verb get">GET</span> `/state/scan`

The latest 360° laser scan.

```json
{ "data": {
    "angle_min": -3.14159, "angle_max": 3.14159,
    "angle_increment": 0.008727,
    "range_min": 0.15, "range_max": 12.0,
    "count": 720,
    "ranges": [1.203, 1.198, null, 1.211, "…"] },
  "age_sec": 0.12 }
```

Beam *i* points at `angle_min + i * angle_increment`, measured counter-clockwise from the
robot's forward axis. Ranges are metres.

**`null` means no return** — out of range, too close, or absorbed. It is not zero, and
treating it as zero puts a phantom obstacle against the robot's hull.

The payload is around 720 numbers. For anything continuous, use the `scan` stream on the
[event socket](events.md) rather than polling this.

---

### <span class="verb get">GET</span> `/state/temperature`

Both temperatures a thermal check needs, in one call.

```json
{ "cpu_c": 55.1, "battery_c": 35.0 }
```

Either can be `null` when unavailable. Note this endpoint returns the values directly
rather than wrapped in `data`/`age_sec` — it is a convenience view over two sources that
have different ages, so a single age would be meaningless. For the freshness of each, use
[`/system/health`](system.md).
