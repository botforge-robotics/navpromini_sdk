# Maps

A map is what navigation localizes against. Build one in [mapping mode](mode.md), save it,
then activate it for navigation.

---

### <span class="verb get">GET</span> `/maps`

```bash
curl -s $ROBOT/maps
```

```json
{ "maps": ["workRoom", "F2020"], "count": 2, "current": "workRoom" }
```

`current` is the last map activated for navigation, which may not be the one running right
now — check [`GET /mode`](mode.md) for that. Before any map has been activated it reads
`"default"`, which is the bucket waypoints fall into when no map is in use — not the name
of a map you can navigate on.

An empty list is <span class="status ok">200</span> with `"maps": []`. A robot with no maps
is a new robot, not a broken one.

---

### <span class="verb post">POST</span> `/maps`

Save the map currently being built. Requires [mapping mode](mode.md).

```bash
curl -s -X POST $ROBOT/maps -H 'Content-Type: application/json' \
     -d '{"name": "workRoom"}'
```

```json
{ "saved": true, "name": "workRoom" }
```

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Simple file name — no `/`, no leading `.` |
| `overwrite` | no | Default `false`. Required to replace an existing map |

**Responses**

| | When |
|---|---|
| <span class="status ok">201</span> | Saved under a new name |
| <span class="status ok">200</span> | Replaced an existing map (`"overwritten": true`) |
| <span class="status err">400 `invalid_name`</span> | Name contains `/` or starts with `.` |
| <span class="status err">409 `map_exists`</span> | Name taken; resend with `overwrite` |
| <span class="status err">500 `save_failed`</span> | The save itself failed |

!!! warning "Overwriting is opt-in"
    Silently replacing a map that a robot navigates by is not something to do by accident —
    every waypoint stored against that map suddenly refers to different geometry. So the
    first attempt fails loudly:

    ```json
    { "error": { "code": "map_exists",
                 "message": "A map named 'workRoom' already exists. Resend with {\"overwrite\": true} to replace it.",
                 "detail": { "name": "workRoom" } } }
    ```

**The pose graph is saved too.** Alongside the map image, the SLAM pose graph is
serialized, which means a saved map can later be *extended* — reload it, drive the parts
you missed, save again — rather than only rebuilt from scratch.

Saving takes a few seconds on a large map.

---

### <span class="verb get">GET</span> `/maps/current`

```bash
curl -s $ROBOT/maps/current
```

```json
{ "current": "workRoom", "mode": "navigation" }
```

The lightweight check for "which map are the waypoints I am about to use measured in?".

---

### <span class="verb delete">DELETE</span> `/maps/{name}`

```bash
curl -s -X DELETE $ROBOT/maps/oldRoom
```

```json
{ "deleted": true, "name": "oldRoom", "detail": "removed oldRoom.yaml, oldRoom.pgm" }
```

| | When |
|---|---|
| <span class="status ok">200</span> | Deleted |
| <span class="status err">404 `map_not_found`</span> | No such map |
| <span class="status err">409 `map_in_use`</span> | Navigation is running on this map |

Deleting the map does **not** delete the waypoints stored against it. They stay, keyed by
map name, and reappear if a map of that name is saved again — which is either convenient or
confusing depending on whether you meant to reuse the name.

---

### <span class="verb post">POST</span> `/maps/{name}/activate`

Switch navigation to a different map.

```bash
curl -s -X POST $ROBOT/maps/F2020/activate
```

```json
{ "mode": "navigation", "map": "F2020", "launch_id": "8c11e4a2-…" }
```

This **restarts the navigation stack** — it is exactly `POST /mode {"mode": "navigation",
"map": "F2020"}`, and exists because "use this map" is what the caller actually means.

!!! warning "Localization is lost"
    The robot has no idea where it is in the new map. Send
    [`POST /navigation/localize`](navigation.md) with an approximate pose and wait for
    `localized: true` before sending goals.

### <span class="verb get">GET</span> `/maps/current/info`

Active map dimensions, resolution, and origin metadata from the current occupancy grid.

```bash
curl -s $ROBOT/maps/current/info
```

```json
{
  "loaded": true,
  "current": "workRoom",
  "width": 800,
  "height": 600,
  "resolution": 0.05,
  "origin": { "x": -20.0, "y": -15.0 }
}
```

Returns `"loaded": false` if no occupancy grid is currently published.

---

### <span class="verb get">GET</span> `/maps/current/image`

Renders the active occupancy grid into a PNG image.

```bash
curl -s "$ROBOT/maps/current/image?rotate=90" -o map.png
```

| Query Parameter | Type | Default | Notes |
|---|---|---|---|
| `rotate` | integer | `90` | Clockwise rotation angle (`0`, `90`, `180`, `270`) |

Returns `image/png` binary content:
- **Unknown space (-1)**: `#0B0F19` (Dark blue-gray)
- **Free space (0)**: `#1E293B` (Slate)
- **Obstacles / walls (>50)**: `#38BDF8` (Sky blue highlight)

<span class="status err">404 `no_map`</span> if no active map is loaded.

---

### <span class="verb get">GET</span> `/maps/current/raw`

Returns the raw RGB565 binary pixel buffer of the active occupancy grid. Includes map dimensions and origin as HTTP headers:
- `X-Map-Width`
- `X-Map-Height`
- `X-Map-Resolution`
- `X-Map-Origin-X`, `X-Map-Origin-Y`
- `X-Map-Rotated`

```bash
curl -s $ROBOT/maps/current/raw -o map.rgb565
```

---

## Getting the actual map over ROS

Alongside the HTTP image endpoints above, the live map is also published as a standard ROS topic, `/map` (`nav_msgs/OccupancyGrid`, latched QoS). High-frequency clients and RViz can subscribe to `/map` directly over rosbridge (`:9090`).

## Where maps live

Maps are stored inside the robot's ROS workspace (`navpromini_mapping/maps`): they are plain `.yaml` + `.pgm` pairs alongside serialized pose graphs.

