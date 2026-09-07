# Maps

A map is what navigation localizes against. Build one in [mapping mode](mode.md), save it,
then activate it for navigation.

---

### <span class="verb get">GET</span> `/maps`

List all saved maps and identify the current active map.

#### Request
- **Method**: `GET`
- **Path**: `/maps`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "maps": ["workRoom", "F2020"],
  "count": 2,
  "current": "workRoom"
}
```

| Field | Type | Description |
|---|---|---|
| `maps` | `array[string]` | List of saved map names on the robot |
| `count` | `integer` | Total number of maps available |
| `current` | `string` | The last map activated for navigation (defaults to `"default"` before activation) |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">500</span> | `internal_error` | Failed to read map directory from disk |

#### Example (cURL)

```bash
curl -s $ROBOT/maps
```

---

### <span class="verb post">POST</span> `/maps`

Save the map currently being built. Requires [mapping mode](mode.md). The pose graph is saved alongside the occupancy grid so the map can later be extended.

#### Request
- **Method**: `POST`
- **Path**: `/maps`
- **Headers**: `Content-Type: application/json`

**Payload:**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | Required | Simple file name for the map (no `/` or leading `.`) |
| `overwrite` | `boolean` | Optional | Default `false`. Set `true` to replace an existing map with the same name |

```json
{
  "name": "workRoom",
  "overwrite": false
}
```

#### Response
- **Status**: <span class="status ok">201 Created</span> (or <span class="status ok">200 OK</span> if overwritten)

```json
{
  "saved": true,
  "name": "workRoom",
  "overwritten": false
}
```

| Field | Type | Description |
|---|---|---|
| `saved` | `boolean` | `true` when the map and pose graph have been written to disk |
| `name` | `string` | The saved map name |
| `overwritten` | `boolean` | `true` if an existing map was replaced |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">400</span> | `invalid_name` | Name contains `/` or starts with `.` |
| <span class="status err">409</span> | `map_exists` | A map with this name exists; resend with `"overwrite": true` |
| <span class="status err">409</span> | `not_in_mapping_mode` | Robot is not currently in mapping mode |
| <span class="status err">500</span> | `save_failed` | Map saver node encountered an internal failure |

#### Example (cURL)

```bash
curl -s -X POST $ROBOT/maps \
     -H 'Content-Type: application/json' \
     -d '{"name": "workRoom", "overwrite": true}'
```

---

### <span class="verb get">GET</span> `/maps/current`

Lightweight check for the active map and current operating mode.

#### Request
- **Method**: `GET`
- **Path**: `/maps/current`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "current": "workRoom",
  "mode": "navigation"
}
```

| Field | Type | Description |
|---|---|---|
| `current` | `string` | Name of the active map |
| `mode` | `string` | Current system mode (`"idle"`, `"mapping"`, or `"navigation"`) |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">500</span> | `internal_error` | Failed to query active map state |

#### Example (cURL)

```bash
curl -s $ROBOT/maps/current
```

---

### <span class="verb delete">DELETE</span> `/maps/{name}`

Delete a saved map by name from the robot's storage.

#### Request
- **Method**: `DELETE`
- **Path**: `/maps/{name}`
- **URL Parameters**:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | Required | Name of the map to delete |

- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "deleted": true,
  "name": "oldRoom",
  "detail": "removed oldRoom.yaml, oldRoom.pgm"
}
```

| Field | Type | Description |
|---|---|---|
| `deleted` | `boolean` | `true` when map files were successfully removed |
| `name` | `string` | Name of the deleted map |
| `detail` | `string` | Summary of files removed from disk |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">404</span> | `map_not_found` | No map exists with the given name |
| <span class="status err">409</span> | `map_in_use` | Cannot delete the map currently loaded in navigation mode |

#### Example (cURL)

```bash
curl -s -X DELETE $ROBOT/maps/oldRoom
```

---

### <span class="verb post">POST</span> `/maps/{name}/activate`

Switch navigation mode to a different map. This restarts the navigation stack with the chosen map.

#### Request
- **Method**: `POST`
- **Path**: `/maps/{name}/activate`
- **URL Parameters**:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | Required | Name of the saved map to load and activate |

- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "mode": "navigation",
  "map": "F2020",
  "launch_id": "8c11e4a2-d591-4c47-9ea8-24314d7a8d50"
}
```

| Field | Type | Description |
|---|---|---|
| `mode` | `string` | The active mode (`"navigation"`) |
| `map` | `string` | The active map name |
| `launch_id` | `string` | Unique identifier for this launch lifecycle instance |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">404</span> | `map_not_found` | Map name does not exist on disk |
| <span class="status err">409</span> | `mode_busy` | A mode change or launch is already running |
| <span class="status err">500</span> | `launch_failed` | Navigation stack failed to initialize with the map |

#### Example (cURL)

```bash
curl -s -X POST $ROBOT/maps/F2020/activate
```

---

### <span class="verb get">GET</span> `/maps/current/info`

Active map dimensions, resolution, and origin coordinates extracted from the current ROS occupancy grid.

#### Request
- **Method**: `GET`
- **Path**: `/maps/current/info`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "loaded": true,
  "current": "workRoom",
  "width": 800,
  "height": 600,
  "resolution": 0.05,
  "origin": {
    "x": -20.0,
    "y": -15.0
  }
}
```

| Field | Type | Description |
|---|---|---|
| `loaded` | `boolean` | `true` if an active occupancy grid is published |
| `current` | `string` | Name of the active map |
| `width` | `integer` | Map width in grid cells |
| `height` | `integer` | Map height in grid cells |
| `resolution` | `number` | Size of each grid cell in metres (e.g. `0.05` = 5 cm/cell) |
| `origin` | `object` | World coordinates of the map's lower-left corner (0,0 cell) |
| `origin.x` | `number` | X origin in metres |
| `origin.y` | `number` | Y origin in metres |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">404</span> | `no_map` | No occupancy grid is published or loaded |

#### Example (cURL)

```bash
curl -s $ROBOT/maps/current/info
```

---

### <span class="verb get">GET</span> `/maps/current/image`

Renders the active occupancy grid into a PNG image suitable for UI display.

#### Request
- **Method**: `GET`
- **Path**: `/maps/current/image`
- **Query Parameters**:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `rotate` | `integer` | Optional | Clockwise rotation angle: `0`, `90`, `180`, or `270` (default: `90`) |

- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>
- **Content-Type**: `image/png`

Binary image data with colour encoding:
- **Unknown space (-1)**: `#0B0F19` (Dark blue-gray)
- **Free space (0)**: `#1E293B` (Slate)
- **Obstacles / walls (>50)**: `#38BDF8` (Sky blue highlight)

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">404</span> | `no_map` | No active occupancy grid is available to render |

#### Example (cURL)

```bash
curl -s "$ROBOT/maps/current/image?rotate=90" -o map.png
```

---

### <span class="verb get">GET</span> `/maps/current/raw`

Returns the raw RGB565 binary pixel buffer of the active occupancy grid, optimized for embedded web canvas rendering.

#### Request
- **Method**: `GET`
- **Path**: `/maps/current/raw`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>
- **Content-Type**: `application/octet-stream`

Binary pixel stream accompanied by map metadata in response headers:

| Header | Type | Description |
|---|---|---|
| `X-Map-Width` | `integer` | Width of the image in pixels |
| `X-Map-Height` | `integer` | Height of the image in pixels |
| `X-Map-Resolution` | `number` | Metres per pixel |
| `X-Map-Origin-X` | `number` | Origin X world coordinate |
| `X-Map-Origin-Y` | `number` | Origin Y world coordinate |
| `X-Map-Rotated` | `integer` | Rotation angle applied to the buffer |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">404</span> | `no_map` | No active occupancy grid loaded |

#### Example (cURL)

```bash
curl -s $ROBOT/maps/current/raw -o map.rgb565
```

---

## Getting the actual map over ROS

Alongside the HTTP image endpoints above, the live map is also published as a standard ROS topic, `/map` (`nav_msgs/OccupancyGrid`, latched QoS). High-frequency clients and RViz can subscribe to `/map` directly over rosbridge (`:9090`).

## Where maps live

Maps are stored inside the robot's ROS workspace (`navpromini_mapping/maps`): they are plain `.yaml` + `.pgm` pairs alongside serialized pose graphs.
