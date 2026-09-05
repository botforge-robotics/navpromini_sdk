# Missions

A mission is a saved, named sequence of steps — navigate here, wait, dock, undock, call an
arbitrary service or action — that runs on the robot as a single unit, optionally repeated.
Saving a mission does not start it; starting is a separate call, so a mission can be
prepared ahead of time or fired later by a [schedule](schedules.md).

---

### <span class="verb get">GET</span> `/missions`

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
| `navigate` | `target` (a waypoint name) **or** `x`/`y` (+ optional `theta`) | Same goal as [`POST /navigation/goto`](navigation.md) |
| `wait` | `duration` (seconds) | Pauses the mission, nothing else |
| `dock` | — | Same as [`POST /dock`](docking.md). Optional `navigate_to_staging` (default `true`) |
| `undock` | — | Same as [`POST /undock`](docking.md) |
| `call_service` | `service`, `service_type` | Calls any ROS service by name + type (e.g. `std_srvs/srv/Trigger`). Optional `request` (object), `timeout` (seconds, default 15) |
| `call_action` | `action`, `action_type` | Sends any ROS action goal by name + type (e.g. `nav2_msgs/action/Spin`). Optional `goal` (object), `timeout` (seconds, default 300) |

!!! warning "`call_service`/`call_action` are as powerful as the robot's own ROS graph"
    These two step types can invoke *anything* reachable over ROS by name — the same trust
    boundary the robot's own internals use, not a new one. `service_type`/`action_type` are
    resolved to a real message class **at save time**, so a typo'd type string fails
    immediately with <span class="status err">400 `invalid_step`</span> instead of days
    later when the mission actually runs unattended.

**Responses**

| | When |
|---|---|
| <span class="status ok">201</span> | Saved |
| <span class="status err">400 `invalid_field`</span> | Missing `id`/`steps`, or a bad `loop_count` |
| <span class="status err">400 `invalid_step`</span> | A step is malformed, or its type is unknown |

---

### <span class="verb get">GET</span> `/missions/{id}`

```json
{ "mission": { "id": "morning-patrol", "name": "Morning patrol", "steps": ["…"] } }
```

<span class="status err">404 `mission_not_found`</span> if no mission has that `id`.

---

### <span class="verb delete">DELETE</span> `/missions/{id}`

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

<span class="status err">409 `mission_not_active`</span> if this mission is not the one
currently running.

---

### <span class="verb post">POST</span> `/missions/{id}/resume`

Clears the pause. Same `mission_not_active` error if this mission is not current.

---

### <span class="verb post">POST</span> `/missions/{id}/cancel`

Stops the mission for good — unlike pause, there is no resuming a cancelled mission. Ends
the whole run, including every remaining loop lap, not just the current one.

---

### <span class="verb get">GET</span> `/missions/status`

The one mission that may be running right now, robot-wide — not scoped to a particular
`{id}`, because only one can ever be active.

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
