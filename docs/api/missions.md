# Missions

A mission is a saved, named sequence of steps — navigate here, wait, dock, undock, call an
arbitrary service or action — that runs on the robot as a single unit, optionally repeated.
Saving a mission does not start it; starting is a separate call, so a mission can be
prepared ahead of time or fired later by a [schedule](schedules.md).

---

### <span class="verb get">GET</span> `/missions`

List all saved missions.

```bash
curl -s $ROBOT/missions
```

```json
{ "missions": [
  { "id": "morning-patrol", "name": "Morning patrol", "steps": ["…"],
    "loop_forever": false, "loop_count": 1 }
] }
```

---

### <span class="verb post">POST</span> `/missions`

Create, or replace by `id` — the same create-or-replace shape as
[`PUT /dock/pose`](docking.md) and [`POST /waypoints`](waypoints.md), just keyed by a
caller-supplied `id` instead of a server-generated one.

```bash
curl -s -X POST $ROBOT/missions -H 'Content-Type: application/json' -d '{
  "id": "morning-patrol",
  "name": "Morning patrol",
  "loop_count": 2,
  "steps": [
    { "type": "navigate", "target": "kitchen" },
    { "type": "wait", "duration": 10 },
    { "type": "navigate", "x": 2.1, "y": -0.4, "theta": 1.57 },
    { "type": "dock" }
  ]
}'
```

```json
{ "mission": { "id": "morning-patrol", "name": "Morning patrol", "steps": ["…"],
               "loop_forever": false, "loop_count": 2 } }
```

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Caller-chosen. Resending the same `id` replaces the mission |
| `steps` | yes | Non-empty list — see **Step types** below |
| `name` | no | Defaults to `id` |
| `loop_count` | no | Repeat the whole step list this many times. Default `1` |
| `loop_forever` | no | Repeat until cancelled, ignoring `loop_count`. Default `false` |

**Step types** — every step needs a `type`:

| `type` | Required fields | What it does |
|---|---|---|
| `navigate` | `waypoint` or `target` (a waypoint name) **or** `x`/`y` (+ optional `theta`) | Same goal as [`POST /navigation/goto`](navigation.md) |
| `wait` | `duration` or `duration_sec` (seconds) | Pauses the mission, nothing else |
| `dock` | — | Same as [`POST /dock`](docking.md). Optional `navigate_to_staging` (default `true`) |
| `undock` | — | Same as [`POST /undock`](docking.md) |
| `call_service` | `service`, `service_type` | Calls any ROS service by name + type (e.g. `std_srvs/srv/Trigger`). Optional `request` (object), `timeout` (seconds, default 15), `ignore_error` (boolean, default `false`) |
| `call_action` | `action` (or `action_name`), `action_type` | Sends any ROS action goal by name + type (e.g. `nav2_msgs/action/Spin`). Optional `goal` (object), `timeout` (seconds, default 300), `ignore_error` (boolean, default `false`) |
| `call_api` | `url` | Performs an HTTP/HTTPS request. Optional `method` (default `POST`), `headers` (dict), `payload` (JSON or string), `timeout` (seconds, default 15), `ignore_error` (boolean, default `false`) |

!!! warning "`call_service`/`call_action` are as powerful as the robot's own ROS graph"
    These two step types can invoke *anything* reachable over ROS by name — the same trust
    boundary the robot's own internals use, not a new one. `service_type`/`action_type` are
    resolved to a real message class **at save time**, so a typo'd type string fails
    immediately with <span class="status err">400 `invalid_step`</span> instead of days
    later when the mission actually runs unattended.

---

### In-Depth Step Type Reference

#### 1. `call_service` — ROS 2 Service Invocations
Executes a synchronous request/response call to any ROS 2 service advertised in the robot's local graph.
Useful for triggering sensors, cameras, clearing costmaps, or resetting microcontroller state.

```json
{
  "type": "call_service",
  "service": "/camera/capture_snapshot",
  "service_type": "std_srvs/srv/Trigger",
  "request": {},
  "timeout": 10.0
}
```

- **`service`** *(string, required)*: The fully qualified ROS 2 service topic name.
- **`service_type`** *(string, required)*: Package and interface name (e.g., `std_srvs/srv/Trigger`, `std_srvs/srv/SetBool`, `sensor_msgs/srv/SetCameraInfo`).
- **`request`** *(object, optional)*: Key-value dictionary matching the fields of the service's Request message. For parameterless services like `Trigger` or `Empty`, pass `{}` or omit.
- **`timeout`** *(number, optional)*: Seconds to wait for service availability and response. Defaults to `15.0`.
- **`ignore_error`** *(boolean, optional)*: If `true`, a failure or timeout when calling this service logs a warning but does not fail the mission. Defaults to `false`.
- **Failure behavior**: If the service is not advertised, returns an error response, or exceeds `timeout`, the step fails, aborting the mission immediately (unless `ignore_error: true`).

```json
// Example: Enable conveyor bridge via SetBool service
{
  "type": "call_service",
  "service": "/conveyor_bridge/enable",
  "service_type": "std_srvs/srv/SetBool",
  "request": { "data": true },
  "timeout": 5.0,
  "ignore_error": false
}
```

---

#### 2. `call_action` — ROS 2 Action Invocations
Dispatches a long-running goal to any ROS 2 Action Server in the robot's graph.
Useful for triggering Nav2 recovery behaviors (e.g., spinning 360°, backing up) or third-party actuators (e.g. robotic arms, lift mechanisms).

```json
{
  "type": "call_action",
  "action": "/spin",
  "action_type": "nav2_msgs/action/Spin",
  "goal": {
    "target_yaw": 3.14159,
    "time_allowance": { "sec": 15, "nanosec": 0 }
  },
  "timeout": 20.0,
  "ignore_error": false
}
```

- **`action`** *(string, required)*: Action server topic name (or alias `action_name`).
- **`action_type`** *(string, required)*: Package and action interface name (e.g. `nav2_msgs/action/Spin`, `nav2_msgs/action/BackUp`).
- **`goal`** *(object, optional)*: Goal fields passed to the Action Server.
- **`timeout`** *(number, optional)*: Maximum duration in seconds to allow for goal execution. Defaults to `300.0`.
- **`ignore_error`** *(boolean, optional)*: If `true`, an action goal rejection or abort logs a warning but does not fail the mission. Defaults to `false`.
- **Failure behavior**: If the action server rejects the goal, aborts mid-execution, or times out, the mission halts with state `failed` (unless `ignore_error: true`).

---

#### 3. `call_api` — Outbound Webhooks & Cloud Integration
Performs an outbound HTTP or HTTPS request from the robot to external systems (Manufacturing Execution Systems [MES], Warehouse Management Systems [WMS], ERPs, Slack/Discord webhooks, or cloud REST APIs).

```json
{
  "type": "call_api",
  "url": "http://mes.factory.local/api/v1/workstation/arrival",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer f4c8e791b...",
    "Content-Type": "application/json"
  },
  "payload": {
    "robot_id": "navpromini-01",
    "station": "assembly_bay_4",
    "status": "arrived_for_pickup"
  },
  "timeout": 10.0,
  "ignore_error": false
}
```

- **`url`** *(string, required)*: Destination HTTP/HTTPS URL reachable from the robot's network.
- **`method`** *(string, optional)*: HTTP verb (`POST`, `GET`, `PUT`, `DELETE`, `PATCH`). Defaults to `POST`.
- **`headers`** *(object, optional)*: Custom headers dictionary (e.g. auth tokens, API keys).
- **`payload`** *(any, optional)*: Request body. Can be a JSON object, list, or string. Automatically serialized.
- **`timeout`** *(number, optional)*: Request timeout in seconds. Defaults to `15.0`.
- **`ignore_error`** *(boolean, optional)*:
  - If `false` (default): A response HTTP status $\ge 400$ or a network timeout terminates the mission with state `failed`.
  - If `true`: The HTTP call is considered a non-fatal fire-and-forget or alert. The mission continues to the next step even if the endpoint is offline.

---

### Complete Multi-Step Mission Example (JSON)

```json
{
  "id": "full-cycle-inspection",
  "name": "Warehouse Inspection with MES Webhook and Arm Trigger",
  "loop_count": 1,
  "steps": [
    {
      "type": "navigate",
      "target": "inspection_bay"
    },
    {
      "type": "call_service",
      "service": "/camera/capture_highres",
      "service_type": "std_srvs/srv/Trigger",
      "timeout": 10.0
    },
    {
      "type": "call_api",
      "url": "https://mes.internal/inspections",
      "method": "POST",
      "headers": { "X-API-Key": "secret-mes-key" },
      "payload": { "station": "inspection_bay", "result": "ready" },
      "ignore_error": true
    },
    {
      "type": "wait",
      "duration": 5.0
    },
    {
      "type": "call_action",
      "action": "/spin",
      "action_type": "nav2_msgs/action/Spin",
      "goal": { "target_yaw": 3.14159 },
      "timeout": 20.0
    },
    {
      "type": "dock",
      "navigate_to_staging": true
    }
  ]
}
```

### Python SDK Usage Example

```python
from navpromini import NavProMini

robot = NavProMini("192.168.1.50")

# Define mission with navigate, call_service, call_api, and dock
steps = [
    {"type": "navigate", "target": "station_a"},
    {
        "type": "call_service",
        "service": "/sensor_relay/trigger",
        "service_type": "std_srvs/srv/Trigger",
        "timeout": 5.0
    },
    {
        "type": "call_api",
        "url": "http://192.168.1.100:8080/events/arrival",
        "method": "POST",
        "payload": {"status": "arrived"},
        "ignore_error": False
    },
    {"type": "dock"}
]

robot.save_mission("station_a_patrol", steps=steps, loop_count=1)
robot.start_mission("station_a_patrol", wait=True)
print("Mission complete!")
```

**Responses**

| | When |
|---|---|
| <span class="status ok">201</span> | Saved |
| <span class="status err">400 `invalid_field`</span> | Missing `id`/`steps`, or a bad `loop_count` |
| <span class="status err">400 `invalid_step`</span> | A step is malformed, or its type is unknown |

---

### <span class="verb get">GET</span> `/missions/{id}`

Retrieve a single saved mission by id.

```bash
curl -s $ROBOT/missions/morning-patrol
```

```json
{ "mission": { "id": "morning-patrol", "name": "Morning patrol", "steps": ["…"] } }
```

<span class="status err">404 `mission_not_found`</span> if no mission has that `id`.

---

### <span class="verb delete">DELETE</span> `/missions/{id}`

Delete a saved mission by id.

```bash
curl -s -X DELETE $ROBOT/missions/morning-patrol
```

```json
{ "deleted": true, "id": "morning-patrol" }
```

| | When |
|---|---|
| <span class="status ok">200</span> | Deleted |
| <span class="status err">404 `mission_not_found`</span> | No such mission |
| <span class="status err">409 `mission_active`</span> | This mission is currently running — cancel it first |

---

### <span class="verb post">POST</span> `/missions/{id}/start`

```bash
curl -s -X POST $ROBOT/missions/morning-patrol/start
```

```json
{ "accepted": true, "mission_id": "morning-patrol" }
```

Returns <span class="status warn">202</span> immediately, the same "accepted, not finished"
shape as [`POST /navigation/goto`](navigation.md) — a mission can run for minutes. Watch
[`GET /missions/status`](#get-missionsstatus) or the [event stream](events.md).

Only **one** mission may run at a time, robot-wide:

| | When |
|---|---|
| <span class="status err">409 `mission_active`</span> | Another mission is already running or paused |
| <span class="status err">404 `mission_not_found`</span> | No such mission |

---

### <span class="verb post">POST</span> `/missions/{id}/pause`

Pauses after the **current step** finishes — not mid-step. A `navigate` step already
underway completes or fails on its own terms; the mission simply does not advance to the
next step until resumed.

```bash
curl -s -X POST $ROBOT/missions/morning-patrol/pause
```

```json
{ "mission_id": "morning-patrol", "state": "paused", "step_index": 2, "message": "" }
```

<span class="status err">409 `mission_not_active`</span> if this mission is not the one
currently running.

---

### <span class="verb post">POST</span> `/missions/{id}/resume`

Clears the pause and resumes execution.

```bash
curl -s -X POST $ROBOT/missions/morning-patrol/resume
```

```json
{ "mission_id": "morning-patrol", "state": "running", "step_index": 2, "message": "" }
```

Same `mission_not_active` error if this mission is not current.

---

### <span class="verb post">POST</span> `/missions/{id}/cancel`

Stops the mission for good — unlike pause, there is no resuming a cancelled mission. Ends
the whole run, including every remaining loop lap, not just the current one.

```bash
curl -s -X POST $ROBOT/missions/morning-patrol/cancel
```

```json
{ "mission_id": "morning-patrol", "state": "canceled", "step_index": 2, "message": "" }
```

---

### <span class="verb get">GET</span> `/missions/status`

The one mission that may be running right now, robot-wide — not scoped to a particular
`{id}`, because only one can ever be active.

```bash
curl -s $ROBOT/missions/status
```

```json
{ "mission_id": "morning-patrol", "state": "running",
  "step_index": 2, "loop_index": 0, "loop_total": 2,
  "message": "", "pause_reason": null, "elapsed_sec": 47.3 }
```

| Field | Meaning |
|---|---|
| `state` | `idle`, `running`, `paused`, `completed`, `failed`, `canceled` |
| `step_index` | Index into `steps`, within the current lap |
| `loop_index` | Which lap this is (`0`-based) |
| `loop_total` | Total laps, or `null` for a `loop_forever` mission — lets a client tell "not looping" from "looping forever" from "lap 2 of 5" without a separate flag |
| `pause_reason` | `null`, `"user"` (paused by API request), or `"low_battery"` (auto-docked for recharge) |
| `message` | Explanatory text or failing step's error once `state` is `failed` |

A failure ends the whole mission, including any remaining loops — a broken step does not
retry itself into the next lap.

---

## Low Battery Auto-Dock and Auto-Resume

During mission execution, the robot continuously monitors battery state of charge (SoC). To ensure mission reliability and protect battery health, automated low-battery safeguarding is built directly into the runner:

- **Trigger Threshold**: When battery SoC drops to $\le 5.0\%$ (configurable via environment variable `NAVPRO_LOW_BATT_DOCK_PCT`), the runner intercepts execution:
  1. Active navigation goals are smoothly canceled.
  2. Mission state transitions to `paused` with `pause_reason: "low_battery"`.
  3. The robot commands an auto-dock sequence to return to the charging station.
  4. Emits a WebSocket event `mission.paused` with `{"reason": "low_battery"}`.
- **Charging and Auto-Resume**:
  - The robot stays parked on the dock while recharging.
  - When battery SoC reaches $\ge 95.0\%$ (configurable via `NAVPRO_RESUME_BATT_PCT`), the robot automatically executes an undock maneuver and resumes the mission from the exact step and lap where it was paused.
  - Emits a WebSocket event `mission.resumed` with `{"reason": "battery_charged"}`.

### Edge Case Handling

| Scenario | Behavior |
|---|---|
| **User cancels while charging** | If `POST /missions/{id}/cancel` or `DELETE /missions/{id}` is called while parked on the charger, the mission is safely canceled, and the runner terminates cleanly. **The robot stays safely docked and continues charging.** |
| **Manual resume override** | If `POST /missions/{id}/resume` is invoked while parked on the dock before 95% charge is reached, the robot immediately undocks and resumes the mission with current charge. |
| **Docking failure on low battery** | If auto-docking fails or gets obstructed, the robot stops immediately, preserves mission pause state, and reports `pause_reason: "low_battery"` with an informative message rather than endlessly looping. |
| **Normal user pause** | Manual pauses set `pause_reason: "user"` and do not initiate automatic docking or automatic resume. |

---

## Missions and the app

The NavPro Mini app's own Mission Planner is a client of this exact API, not a separate
system — a mission created from the app shows up here, and one created with `curl` shows up
in the app.
