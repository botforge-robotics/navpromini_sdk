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

---

## Where maps live

Maps are stored inside the robot's ROS install tree rather than in a separate data
directory.

!!! danger "A clean rebuild of the robot workspace can remove saved maps"
    This is a property of the robot's workspace layout, not of the API, and the API does not
    paper over it — the fix belongs where the problem is. If maps matter, copy them off the
    robot: they are plain `.yaml` + `.pgm` pairs.
