# Motion

Direct control, bypassing the navigation stack. Works in any [mode](mode.md), including
idle.

!!! danger "No obstacle avoidance"
    These endpoints drive the wheels. Nothing checks the lidar first. Use them for teleop
    with a human watching, for short deliberate manoeuvres, and for driving during mapping —
    not for autonomous movement across a space. For that, use
    [`/navigation/goto`](navigation.md), which plans around obstacles.

---

### <span class="verb post">POST</span> `/motion/velocity`

Continuous velocity. This is the teleop primitive.

```bash
curl -s -X POST $ROBOT/motion/velocity -H 'Content-Type: application/json' \
     -d '{"linear": 0.15, "angular": 0.0}'
```

```json
{ "linear": 0.15, "angular": 0.0, "expires_in_sec": 0.5 }
```

| Field | Default | Limit |
|---|---|---|
| `linear` | `0` | ±0.35 m/s, forward positive |
| `angular` | `0` | ±1.2 rad/s, counter-clockwise positive |

!!! warning "Commands expire after ~0.5 s — repeat at about 5 Hz"
    This is the safety property, not an inconvenience. An HTTP client that crashes
    mid-drive, or a WiFi link that drops, must not leave a robot driving into a wall. If
    commands stop arriving, the robot stops.

```python
import time, requests

ROBOT = "http://navpromini.local:8090/api/v1"
end = time.time() + 3.0
while time.time() < end:                       # drive forward for 3 seconds
    requests.post(f"{ROBOT}/motion/velocity", json={"linear": 0.15})
    time.sleep(0.2)                            # 5 Hz
requests.post(f"{ROBOT}/motion/stop")
```

Values beyond the limits are rejected rather than clamped:

```json
{ "error": { "code": "out_of_range",
             "message": "linear must be within +/-0.35",
             "detail": { "field": "linear", "limit": 0.35, "given": 5.0 } } }
```

The limits match the robot's configured navigation limits. The API is not a way around the
speed limits the rest of the stack respects — a caller asking for 5 m/s gets a clear
<span class="status err">400</span>, not a robot that tries.

Direct motion runs at the teleop priority: an emergency stop overrides it, and it does not
fight the navigation stack for control.

---

### <span class="verb post">POST</span> `/motion/stop`

```bash
curl -s -X POST $ROBOT/motion/stop
```

```json
{ "stopped": true }
```

Zero velocity, immediately. Idempotent — call it as often as you like.

!!! info "Stop does not cancel a navigation goal"
    It zeroes the velocity command, but the navigation stack will keep issuing its own. To
    stop an autonomous goal, use
    [`DELETE /navigation/goal`](navigation.md#delete-navigationgoal); to stop a dock, that
    is `POST /motion/stop` plus waiting for the operation to give up. `/motion/stop` is the
    right call for teleop and for an emergency halt of direct motion.

---

### <span class="verb post">POST</span> `/motion/move`

Drive a fixed distance in a straight line, then stop.

```bash
curl -s -X POST $ROBOT/motion/move -H 'Content-Type: application/json' \
     -d '{"distance": 0.4, "speed": 0.1}'
```

```json
{ "accepted": true, "distance": 0.4, "speed": 0.1 }
```

| Field | Required | Default | Limit |
|---|---|---|---|
| `distance` | yes | — | ±5 m. Negative reverses |
| `speed` | no | `0.1` | 0.35 m/s. Always positive |

Unlike `/motion/velocity`, this does not need repeating — the robot executes the whole
move. It returns as soon as the move is accepted, not when it completes.

Distance comes from wheel odometry, so it accumulates error on slippery floors. Over the
short distances this is meant for, that error is small.

---

### <span class="verb post">POST</span> `/motion/rotate`

Rotate in place.

```bash
curl -s -X POST $ROBOT/motion/rotate -H 'Content-Type: application/json' \
     -d '{"angle": 1.5708}'
```

```json
{ "accepted": true, "angle": 1.5708 }
```

| Field | Required | Default | Limit |
|---|---|---|---|
| `angle` | yes | — | ±2π radians. Positive is counter-clockwise |
| `speed` | no | `0.3` | rad/s |

To turn 90° left, send `1.5708`. To turn right, `-1.5708`.

Rotation also comes from odometry and tends to slightly overshoot on a robot with
low-latency wheels and a heavier chassis. For precise heading, navigate to a pose with a
`theta` instead — the navigation stack closes the loop against the map.

---

## Choosing an endpoint

| You want | Use |
|---|---|
| Joystick / gamepad teleop | `/motion/velocity` at 5 Hz |
| Nudge forward 20 cm | `/motion/move` |
| Turn to face a direction | `/motion/rotate` |
| Stop right now | `/motion/stop` |
| Cross a room safely | [`/navigation/goto`](navigation.md) |
| Return to the charger | [`/dock`](docking.md) |
