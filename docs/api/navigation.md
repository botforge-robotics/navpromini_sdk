# Navigation

Send the robot somewhere and follow what happens. Requires
[navigation mode](mode.md) and a localized robot.

---

### <span class="verb post">POST</span> `/navigation/goto`

=== "By waypoint name"

    ```bash
    curl -s -X POST $ROBOT/navigation/goto -H 'Content-Type: application/json' \
         -d '{"waypoint": "kitchen"}'
    ```

=== "By coordinates"

    ```bash
    curl -s -X POST $ROBOT/navigation/goto -H 'Content-Type: application/json' \
         -d '{"x": 2.4, "y": 1.1, "theta": 1.57}'
    ```

```json
{ "accepted": true,
  "target": { "waypoint": "kitchen", "x": 1.5, "y": -0.4, "theta": 0.2 } }
```

| Field | Required | Notes |
|---|---|---|
| `waypoint` | either this… | Name from [`/waypoints`](waypoints.md) |
| `x`, `y` | …or these | Map-frame metres |
| `theta` | no | Heading on arrival, radians. Default `0` |
| `replace` | no | Cancel any running goal and take over |

**Responses**

| | When |
|---|---|
| <span class="status warn">202</span> | Goal accepted — the robot is moving |
| <span class="status err">400 `missing_field`</span> | Neither a `waypoint` nor both `x` and `y` |
| <span class="status err">404 `waypoint_not_found`</span> | No such waypoint in the current map |
| <span class="status err">409 `goal_active`</span> | A goal is already running |
| <span class="status err">503 `action_unavailable`</span> | Navigation is not running |

!!! info "202 means accepted, not arrived"
    Crossing a room takes minutes — longer than any sane HTTP timeout and longer than most
    proxies allow. The call returns the moment the robot *accepts* the goal. A goal can be
    accepted and then fail because the path is blocked; only `/navigation/status` or the
    [event stream](events.md) tells you which happened.

!!! tip "A docked robot undocks itself first"
    Goals are routed through the robot's dock-aware entry point, so sending a goal to a
    docked robot makes it leave the charger cleanly and then drive. You never need to
    undock manually before navigating — and a docked robot can never be told to drive off
    while still on the contacts.

**One goal at a time.** A second goal returns <span class="status err">409</span> carrying
the running one in `detail.current`, so you can decide what to do:

```json
{ "error": { "code": "goal_active",
             "message": "A navigation goal is already running. Cancel it, or resend with {\"replace\": true}.",
             "detail": { "current": { "state": "active",
                                      "target": { "waypoint": "kitchen" },
                                      "elapsed_sec": 12.4 } } } }
```

That friction is deliberate. Two subsystems both sending goals is a real failure mode, and
letting the last writer win silently makes it invisible. `"replace": true` says "I know
something may be running, cancel it".

---

### <span class="verb get">GET</span> `/navigation/status`

```json
{ "state": "active",
  "target": { "waypoint": "kitchen", "x": 1.5, "y": -0.4, "theta": 0.2 },
  "message": "",
  "elapsed_sec": 12.4,
  "distance_remaining": 3.271 }
```

| `state` | Meaning |
|---|---|
| `idle` | No goal has been sent this session |
| `active` | Driving |
| `succeeded` | Arrived |
| `canceled` | Cancelled, by you or by another client |
| `failed` | Gave up — `message` says why |

`distance_remaining` is **straight-line** distance to the target, present only while the
robot is localized. The path around furniture is longer; use it as progress, not as an ETA.

After a goal finishes the terminal state persists until the next goal, so a client that
polls slowly still sees the outcome rather than a bare `idle`.

---

### <span class="verb delete">DELETE</span> `/navigation/goal`

```bash
curl -s -X DELETE $ROBOT/navigation/goal
```

```json
{ "canceled": true }
```

Cancelling when nothing is running is <span class="status ok">200</span>, not an error:

```json
{ "canceled": false, "reason": "no active goal" }
```

Cancel is idempotent because it is what a client calls when it is *unsure* of the state,
and an error there would just be noise.

Cancel decelerates the robot through the navigation stack. For an immediate halt, use
[`POST /motion/stop`](motion.md).

---

### <span class="verb post">POST</span> `/navigation/localize`

Tell the robot roughly where it is — the equivalent of "2D Pose Estimate" in a robot UI.

```bash
curl -s -X POST $ROBOT/navigation/localize -H 'Content-Type: application/json' \
     -d '{"x": 0.0, "y": 0.0, "theta": 0.0}'
```

```json
{ "x": 0.0, "y": 0.0, "theta": 0.0 }
```

| Field | Required |
|---|---|
| `x`, `y` | yes |
| `theta` | no, default `0` |

Needed after starting navigation, after switching maps, and any time localization is lost.

**Accuracy of a few tens of centimetres is enough** — the particle filter converges from
there once the robot moves. Heading matters more than position: a pose 180° out will not
converge at all, because the lidar sees a mirror image of what it expects.

Verify with `GET /state/pose` until `localized` is `true` and the pose stops jumping.

---

### <span class="verb post">POST</span> `/navigation/relocalize/global`

Triggers AMCL's global localization service (`/reinitialize_global_localization`) to disperse particles uniformly across the entire active map. Use when the robot is completely lost or kidnapped, and allow the robot to rotate or drive so particles converge on its true pose.

```bash
curl -s -X POST $ROBOT/navigation/relocalize/global
```

```json
{ "status": "ok", "message": "AMCL particles dispersed across map" }
```

---

### <span class="verb get">GET</span> `/navigation/path`

The planned route for the current goal.

```json
{ "data": [ { "x": 0.99, "y": -0.36 }, { "x": 1.04, "y": -0.33 }, "…" ],
  "age_sec": 0.4 }
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
