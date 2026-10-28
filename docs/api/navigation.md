# Navigation

Send the robot somewhere and follow what happens. Requires
[navigation mode](mode.md) and a localized robot.

---

### <span class="verb post">POST</span> `/navigation/goto`

Command the AMR to drive autonomously to a named waypoint or map coordinates.

#### Request
- **Method**: `POST`
- **Path**: `/navigation/goto`
- **Headers**: `Content-Type: application/json`

**Payload:**

| Field | Type | Required | Description |
|---|---|---|---|
| `waypoint` | `string` | Either this... | Saved waypoint name from [`/waypoints`](waypoints.md) |
| `x`, `y` | `number` | ...or these | Target position in metres (map frame) |
| `theta` | `number` | Optional | Target heading on arrival in radians (default: `0.0`) |
| `replace` | `boolean` | Optional | If `true`, cancels any in-flight navigation goal and takes over (default: `false`) |

```json
{
  "waypoint": "kitchen",
  "replace": true
}
```

#### Response
- **Status**: <span class="status warn">202 Accepted</span>

```json
{
  "accepted": true,
  "target": { "waypoint": "kitchen", "x": 1.5, "y": -0.4, "theta": 0.2 }
}
```

| Field | Type | Description |
|---|---|---|
| `accepted` | `boolean` | `true` when the navigation goal has been accepted by Nav2 |
| `target` | `object` | Resolved destination coordinates and optional waypoint name |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">400</span> | `missing_field` | Neither a `waypoint` nor both `x` and `y` were provided |
| <span class="status err">404</span> | `waypoint_not_found` | No such waypoint exists in the active map |
| <span class="status err">409</span> | `goal_active` | A navigation goal is already running; cancel it first or pass `"replace": true` |
| <span class="status err">503</span> | `action_unavailable` | Navigation stack is not running |

#### Example (cURL)

=== "By waypoint name"

    ```bash
    curl -s -X POST $ROBOT/navigation/goto \
         -H 'Content-Type: application/json' \
         -d '{"waypoint": "kitchen"}'
    ```

=== "By coordinates"

    ```bash
    curl -s -X POST $ROBOT/navigation/goto \
         -H 'Content-Type: application/json' \
         -d '{"x": 2.4, "y": 1.1, "theta": 1.57}'
    ```

---

### <span class="verb get">GET</span> `/navigation/status`

Current execution state, progress, and remaining distance of the active goal.

#### Request
- **Method**: `GET`
- **Path**: `/navigation/status`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "state": "active",
  "target": { "waypoint": "kitchen", "x": 1.5, "y": -0.4, "theta": 0.2 },
  "message": "",
  "elapsed_sec": 12.4,
  "distance_remaining": 3.271
}
```

| Field | Type | Description |
|---|---|---|
| `state` | `string` | Goal state: `idle`, `active`, `succeeded`, `canceled`, or `failed` |
| `target` | `object` | Goal coordinates and waypoint name |
| `message` | `string` | Failure cause or abort reason (empty during active driving) |
| `elapsed_sec` | `number` | Seconds since the goal was dispatched |
| `distance_remaining` | `number` | Straight-line Euclidean distance in metres to the target pose |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">401</span> | `unauthorized` | Token authentication enabled and Bearer token missing/invalid |

#### Example (cURL)

```bash
curl -s $ROBOT/navigation/status
```

---

### <span class="verb delete">DELETE</span> `/navigation/goal`

Cancel the currently executing navigation goal.

#### Request
- **Method**: `DELETE`
- **Path**: `/navigation/goal`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "canceled": true
}
```

| Field | Type | Description |
|---|---|---|
| `canceled` | `boolean` | `true` if an active goal was aborted, `false` if the robot was already idle |
| `reason` | `string` | Optional context if no goal was running (e.g. `"no active goal"`) |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">401</span> | `unauthorized` | Token authentication enabled and Bearer token missing/invalid |

#### Example (cURL)

```bash
curl -s -X DELETE $ROBOT/navigation/goal
```

---

### <span class="verb post">POST</span> `/navigation/localize`

Seed AMCL localization with an initial approximate pose estimate.

#### Request
- **Method**: `POST`
- **Path**: `/navigation/localize`
- **Headers**: `Content-Type: application/json`

**Payload:**

| Field | Type | Required | Description |
|---|---|---|---|
| `x`, `y` | `number` | Yes | Map-frame coordinates in metres |
| `theta` | `number` | Optional | Map heading in radians (default: `0.0`) |

```json
{
  "x": 0.0,
  "y": 0.0,
  "theta": 0.0
}
```

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "x": 0.0,
  "y": 0.0,
  "theta": 0.0
}
```

| Field | Type | Description |
|---|---|---|
| `x`, `y` | `number` | Seed coordinates published to `/initialpose` |
| `theta` | `number` | Heading angle set |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">400</span> | `missing_field` | `x` or `y` is missing |
| <span class="status err">503</span> | `action_unavailable` | Navigation mode is not active |

#### Example (cURL)

```bash
curl -s -X POST $ROBOT/navigation/localize \
     -H 'Content-Type: application/json' \
     -d '{"x": 0.0, "y": 0.0, "theta": 0.0}'
```

---

### <span class="verb post">POST</span> `/navigation/route`

Command the AMR to drive strictly along defined **Road Network** lanes and junctions. See [Road Network](road_network.md) for topology management.

#### Request
- **Method**: `POST`
- **Path**: `/navigation/route`
- **Headers**: `Content-Type: application/json`

**Payload:**

| Field | Type | Required | Description |
|---|---|---|---|
| `goal_id` | `string` | Either this... | Road network node identifier (e.g. `"node_4"`) |
| `waypoint` | `string` | ...or this | Saved waypoint name (resolved along nearest road network junction) |
| `x`, `y` | `number` | ...or coordinates | Explicit destination coordinates |
| `start_id` | `string` | Optional | Start node identifier (defaults to closest node to current robot pose) |
| `theta` | `number` | Optional | Target heading angle in radians (default: `0.0`) |
| `reroute_policy` | `string` | Optional | Obstacle blockage policy: `wait_then_reroute` (default), `immediate`, or `halt_only` |
| `wait_timeout_sec` | `number` | Optional | Seconds to pause before rerouting around obstacle (default: `5.0`) |
| `replace` | `boolean` | Optional | If `true`, supersedes active goal (default: `false`) |

```json
{
  "goal_id": "node_4",
  "reroute_policy": "wait_then_reroute",
  "wait_timeout_sec": 5.0,
  "replace": true
}
```

#### Response
- **Status**: <span class="status warn">202 Accepted</span>

```json
{
  "accepted": true,
  "routing_mode": "road_network",
  "target": {
    "goal_id": "node_4",
    "routing_mode": "road_network",
    "reroute_policy": "wait_then_reroute",
    "wait_timeout_sec": 5.0
  }
}
```

#### Example (cURL)

```bash
curl -s -X POST $ROBOT/navigation/route \
     -H 'Content-Type: application/json' \
     -d '{"goal_id": "node_4", "reroute_policy": "wait_then_reroute"}'
```

---

### <span class="verb post">POST</span> `/navigation/relocalize/global`

Disperse AMCL particle cloud uniformly across the entire map space and autonomously scan surroundings to recover from lost or kidnapped robot state.

#### Request
- **Method**: `POST`
- **Path**: `/navigation/relocalize/global`
- **Headers**: `Content-Type: application/json`

**Payload (Optional):**

| Field | Type | Default | Description |
|---|---|---|---|
| `spin` | `boolean` | `true` | If `true`, undocks if docked and executes autonomous in-place rotation scan cycles with covariance monitoring until localized |
| `angular_vel` | `number` | `0.38` | Scan rotation speed in radians per second |
| `max_tries` | `integer` | `3` | Maximum 360-degree rotation scan sweeps before timeout |
| `timeout_sec` | `number` | `50.0` | Maximum overall duration allowed |
| `target_cov` | `number` | `0.15` | Position covariance threshold in m² for convergence |
| `target_cov_yaw` | `number` | `0.12` | Yaw covariance threshold in rad² for convergence |

```json
{
  "spin": true,
  "max_tries": 3,
  "timeout_sec": 50.0
}
```

#### Response
- **Status**: <span class="status ok">200 OK</span>

=== "Autonomous Auto-Spin Scan (Default)"

    ```json
    {
      "status": "ok",
      "converged": true,
      "tries": 1,
      "elapsed_sec": 14.2,
      "covariance": {
        "cov_x": 0.042,
        "cov_y": 0.038,
        "cov_yaw": 0.081
      },
      "message": "Relocalized successfully in 14.2s (1 scan cycles). AMCL converged."
    }
    ```

=== "Disperse Particles Only (`spin: false`)"

    ```json
    {
      "status": "ok",
      "message": "AMCL particles dispersed across map"
    }
    ```

| Field | Type | Description |
|---|---|---|
| `status` | `string` | Execution verdict (`ok` or `timeout`) |
| `converged` | `boolean` | `true` if AMCL position and yaw covariance met convergence thresholds |
| `tries` | `integer` | Number of 360-degree scan sweeps completed |
| `elapsed_sec` | `number` | Total elapsed scan duration |
| `covariance` | `object` | Final AMCL covariance values (`cov_x`, `cov_y`, `cov_yaw`) |
| `message` | `string` | Outcome summary |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">503</span> | `action_unavailable` | Navigation mode is not active |
| <span class="status err">503</span> | `service_unavailable` | AMCL `/reinitialize_global_localization` service unavailable |

#### Example (cURL)

=== "Full autonomous recovery (disperse + scan)"

    ```bash
    curl -s -X POST $ROBOT/navigation/relocalize/global \
         -H 'Content-Type: application/json' \
         -d '{"spin": true, "max_tries": 3}'
    ```

=== "Disperse particles only"

    ```bash
    curl -s -X POST $ROBOT/navigation/relocalize/global \
         -H 'Content-Type: application/json' \
         -d '{"spin": false}'
    ```

---

### <span class="verb post">POST</span> `/navigation/relocalize/recover`

Execute autonomous multi-cycle particle convergence recovery. Disperses particles across map space and rotates in alternating directions while tracking live covariance until AMCL converges.

#### Request
- **Method**: `POST`
- **Path**: `/navigation/relocalize/recover`
- **Headers**: `Content-Type: application/json`

```json
{
  "max_tries": 3,
  "timeout_sec": 50.0
}
```

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "status": "ok",
  "converged": true,
  "tries": 1,
  "elapsed_sec": 14.8,
  "covariance": {
    "cov_x": 0.038,
    "cov_y": 0.031,
    "cov_yaw": 0.075
  },
  "message": "Relocalized successfully in 14.8s (1 scan cycles). AMCL converged."
}
```

#### Example (cURL)

```bash
curl -s -X POST $ROBOT/navigation/relocalize/recover \
     -H 'Content-Type: application/json' \
     -d '{"max_tries": 3}'
```

---

### <span class="verb get">GET</span> `/navigation/path`

Current planned global trajectory points from robot to goal.

#### Request
- **Method**: `GET`
- **Path**: `/navigation/path`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "data": [
    { "x": 0.99, "y": -0.36 },
    { "x": 1.04, "y": -0.33 }
  ],
  "age_sec": 0.4
}
```

| Field | Type | Description |
|---|---|---|
| `data` | `array` | List of waypoints `{x, y}` along the planned path in map frame |
| `age_sec` | `number` | Seconds since the planner recalculated the path |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">503</span> | `no_data` | No path planned yet or robot is not currently navigating |

#### Example (cURL)

```bash
curl -s $ROBOT/navigation/path
```

Map-frame points from the robot to the target, for drawing on a UI. The planner
**replans continuously** as obstacles appear, so this changes while the robot drives.
<span class="status err">503 `no_data`</span> when nothing has been planned yet.

---

## A complete run

```bash
export ROBOT=http://192.168.1.50:8090/api/v1

curl -s -X POST $ROBOT/mode -H 'Content-Type: application/json' \
     -d '{"mode":"navigation","map":"workRoom"}'

sleep 10                                                   # let Nav2 come up

curl -s -X POST $ROBOT/navigation/localize -H 'Content-Type: application/json' \
     -d '{"x":0,"y":0,"theta":0}'

curl -s -X POST $ROBOT/navigation/goto -H 'Content-Type: application/json' \
     -d '{"waypoint":"kitchen"}'

# wait for a terminal state
while true; do
  state=$(curl -s $ROBOT/navigation/status | python3 -c 'import sys,json;print(json.load(sys.stdin)["state"])')
  echo "$state"
  [ "$state" = "active" ] || break
  sleep 1
done

curl -s -X POST $ROBOT/dock                                # go home and charge
```

Polling in a loop is fine for a script. For anything long-lived, subscribe to the
[event stream](events.md) instead.
