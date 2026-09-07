# Motion

Direct motor control, bypassing the autonomous navigation stack. Operates in any [mode](mode.md), including idle.

!!! danger "No obstacle avoidance"
    These endpoints drive the wheels directly without obstacle checking from lidar. Use them for teleoperation with human oversight, short deliberate calibration maneuvers, or manual mapping. For autonomous path-planned traversal, use [`POST /navigation/goto`](navigation.md).

---

### <span class="verb post">POST</span> `/motion/velocity`

Stream continuous linear and angular velocity commands. This is the primary primitive for joystick and gamepad teleoperation.

!!! warning "Watchdog safety timeout (~0.5 s)"
    Commands automatically expire after approximately 0.5 seconds if not renewed. For continuous motion, stream commands at **5 Hz**. If the network disconnects or the client crashes, the robot halts automatically.

#### Request
- **Method**: `POST`
- **Path**: `/motion/velocity`
- **Headers**: `Content-Type: application/json`

**Payload:**

| Field | Type | Required | Default | Limit | Description |
|---|---|---|---|---|---|
| `linear` | `number` | Optional | `0.0` | `±0.35` m/s | Forward/backward velocity (forward positive) |
| `angular` | `number` | Optional | `0.0` | `±1.2` rad/s | Rotational velocity (counter-clockwise positive) |

```json
{
  "linear": 0.15,
  "angular": 0.0
}
```

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "linear": 0.15,
  "angular": 0.0,
  "expires_in_sec": 0.5
}
```

| Field | Type | Description |
|---|---|---|
| `linear` | `number` | Applied linear velocity in m/s |
| `angular` | `number` | Applied angular velocity in rad/s |
| `expires_in_sec` | `number` | Seconds before watchdog halts motion if no new command is received |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">400</span> | `out_of_range` | Requested velocity exceeds hardware safety limits (max 0.35 m/s, 1.2 rad/s) |

#### Example (cURL)

```bash
curl -s -X POST $ROBOT/motion/velocity \
     -H 'Content-Type: application/json' \
     -d '{"linear": 0.15, "angular": 0.0}'
```

##### Python Teleoperation Loop (5 Hz)

```python
import time, requests

ROBOT = "http://192.168.1.50:8090/api/v1"
end_time = time.time() + 3.0

while time.time() < end_time:                      # drive forward for 3 seconds
    requests.post(f"{ROBOT}/motion/velocity", json={"linear": 0.15})
    time.sleep(0.2)                               # 5 Hz streaming rate

requests.post(f"{ROBOT}/motion/stop")
```

---

### <span class="verb post">POST</span> `/motion/stop`

Immediately command zero velocity to both wheels.

!!! info "Stop behavior"
    Zeroes the direct velocity command immediately. Does not cancel an active Nav2 goal; use [`DELETE /navigation/goal`](navigation.md) to cancel navigation goals.

#### Request
- **Method**: `POST`
- **Path**: `/motion/stop`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "stopped": true
}
```

| Field | Type | Description |
|---|---|---|
| `stopped` | `boolean` | `true` when zero velocity is commanded to base motors |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">500</span> | `internal_error` | Failed to transmit zero-velocity message to base driver |

#### Example (cURL)

```bash
curl -s -X POST $ROBOT/motion/stop
```

---

### <span class="verb post">POST</span> `/motion/move`

Drive a fixed distance in a straight line, then come to a controlled stop.

#### Request
- **Method**: `POST`
- **Path**: `/motion/move`
- **Headers**: `Content-Type: application/json`

**Payload:**

| Field | Type | Required | Default | Limit | Description |
|---|---|---|---|---|---|
| `distance` | `number` | Required | — | `±5.0` m | Travel distance in metres (negative values reverse) |
| `speed` | `number` | Optional | `0.1` | `0.35` m/s | Travel speed in m/s (always positive) |

```json
{
  "distance": 0.4,
  "speed": 0.1
}
```

#### Response
- **Status**: <span class="status warn">202 Accepted</span>

```json
{
  "accepted": true,
  "distance": 0.4,
  "speed": 0.1
}
```

| Field | Type | Description |
|---|---|---|
| `accepted` | `boolean` | `true` when displacement motion is queued |
| `distance` | `number` | Target distance to travel |
| `speed` | `number` | Travel speed setting |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">400</span> | `missing_field` | `distance` parameter was omitted |
| <span class="status err">400</span> | `out_of_range` | Distance or speed exceeds safe threshold |

#### Example (cURL)

```bash
curl -s -X POST $ROBOT/motion/move \
     -H 'Content-Type: application/json' \
     -d '{"distance": 0.4, "speed": 0.1}'
```

---

### <span class="verb post">POST</span> `/motion/rotate`

Rotate the robot in place by a fixed relative angle using wheel odometry feedback.

#### Request
- **Method**: `POST`
- **Path**: `/motion/rotate`
- **Headers**: `Content-Type: application/json`

**Payload:**

| Field | Type | Required | Default | Limit | Description |
|---|---|---|---|---|---|
| `angle` | `number` | Required | — | `±6.283` rad | Angle to rotate in radians (positive = counter-clockwise, negative = clockwise) |
| `speed` | `number` | Optional | `0.3` | `1.2` rad/s | Rotational angular speed in rad/s |

```json
{
  "angle": 1.5708,
  "speed": 0.3
}
```

#### Response
- **Status**: <span class="status warn">202 Accepted</span>

```json
{
  "accepted": true,
  "angle": 1.5708
}
```

| Field | Type | Description |
|---|---|---|
| `accepted` | `boolean` | `true` when in-place rotation is queued |
| `angle` | `number` | Angle commanded |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">400</span> | `missing_field` | `angle` parameter was omitted |
| <span class="status err">400</span> | `out_of_range` | Angle or rotational speed exceeds limits |

#### Example (cURL)

```bash
# Rotate 90 degrees left (π/2 ≈ 1.5708 rad)
curl -s -X POST $ROBOT/motion/rotate \
     -H 'Content-Type: application/json' \
     -d '{"angle": 1.5708}'
```

---

## Endpoint Summary

| Use Case | Endpoint | Notes |
|---|---|---|
| Joystick / gamepad teleop | `POST /motion/velocity` | Stream at 5 Hz |
| Precise relative nudge | `POST /motion/move` | Uses wheel odometry |
| Turn to face direction | `POST /motion/rotate` | Uses wheel odometry |
| Emergency motion halt | `POST /motion/stop` | Immediate zero-velocity |
| Autonomous navigation | [`POST /navigation/goto`](navigation.md) | Obstacle avoidance & path planning |
| Return to charging dock | [`POST /dock`](docking.md) | Visual servoing onto contacts |
