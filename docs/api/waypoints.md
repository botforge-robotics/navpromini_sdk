# Waypoints

Named poses stored on the robot, so a client can say "go to `kitchen`" instead of carrying
coordinates around.

Waypoints are stored **per map**. The same name in two maps is two different places, and
conflating them would send the robot to a coordinate that happens to exist in both.

---

### <span class="verb get">GET</span> `/waypoints`

```bash
curl -s $ROBOT/waypoints
curl -s "$ROBOT/waypoints?map=F2020"
```

```json
{ "map": "workRoom",
  "waypoints": [
    { "name": "kitchen", "type": "waypoint", "x": 1.5,  "y": -0.4, "theta": 0.2 },
    { "name": "charger", "type": "dock",     "x": 0.0,  "y": 0.0,  "theta": 0.0 }
  ] }
```

| Query | Default |
|---|---|
| `map` | The current map |

With no map activated, the current map reads `"default"` — a real bucket that waypoints
can be stored in, but not one navigation can use. Waypoints saved there are only reachable
once you copy them to a real map.

---

### <span class="verb post">POST</span> `/waypoints`

Create or replace a waypoint. Two ways to give the position:

=== "Capture where the robot is"

    The usual way: drive there, then name it.

    ```bash
    curl -s -X POST $ROBOT/waypoints -H 'Content-Type: application/json' \
         -d '{"name": "kitchen"}'
    ```

    ```json
    { "waypoint": { "name": "kitchen", "type": "waypoint",
                    "x": 1.5023, "y": -0.4017, "theta": 0.2044 },
      "source": "current_pose" }
    ```

=== "Give coordinates"

    ```bash
    curl -s -X POST $ROBOT/waypoints -H 'Content-Type: application/json' \
         -d '{"name": "kitchen", "x": 1.5, "y": -0.4, "theta": 0.2}'
    ```

    ```json
    { "waypoint": { "name": "kitchen", "type": "waypoint",
                    "x": 1.5, "y": -0.4, "theta": 0.2 },
      "source": "given" }
    ```

`source` tells you which path was taken — useful when a client is unsure whether its `x`
was actually used.

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Non-empty. An existing name is replaced, not rejected |
| `x`, `y` | no | Both or neither. Omit to capture the current pose |
| `theta` | no | Radians. Default `0` |
| `type` | no | `waypoint` (default), `dock`, `pickup`, `dropoff`, `home` |
| `map` | no | Defaults to the current map |

`type` carries no behaviour in the SDK — the robot navigates to all of them the same way.
It exists so a fleet client can label its own semantics without keeping a parallel database
of what each name means.

**Responses**

| | When |
|---|---|
| <span class="status ok">201</span> | Stored |
| <span class="status err">400 `invalid_field`</span> | Empty name, or an unknown `type` |
| <span class="status err">409 `not_localized`</span> | Capture requested, but there is no map-frame pose |

!!! warning "Capture needs localization"
    Capturing the current pose requires navigation running **and** the robot localized. In
    idle or mapping mode there is no map-frame pose, only an odom one — and odom
    coordinates mean nothing between sessions.

    ```json
    { "error": { "code": "not_localized",
                 "message": "No map-frame pose available, so the current position cannot be saved. Start navigation and localize first, or pass x/y explicitly." } }
    ```

    Passing `x`/`y` explicitly works in any mode, because then you are asserting map
    coordinates rather than asking the robot for them.

---

### <span class="verb get">GET</span> `/waypoints/{name}`

```json
{ "waypoint": { "name": "kitchen", "type": "waypoint",
                "x": 1.5, "y": -0.4, "theta": 0.2 } }
```

Add `?map=<name>` to read from a map other than the current one.
<span class="status err">404 `waypoint_not_found`</span> if there is no such name **in that
map** — worth remembering when a waypoint you are sure exists comes back missing.

---

### <span class="verb delete">DELETE</span> `/waypoints/{name}`

```json
{ "deleted": true, "name": "kitchen" }
```

<span class="status err">404 `waypoint_not_found`</span> if it was not there.

---

## Storage

Waypoints persist in a JSON file on the robot, written atomically — a power cut during a
write leaves the previous version intact rather than a truncated file. They survive
reboots, SDK restarts and app updates.

They are **not** included when you copy a map off the robot. To move a set of waypoints,
`GET /waypoints` on the source robot and `POST` each one to the destination.
