# Waypoints

Named poses stored on the robot, so a client can say "go to `kitchen`" instead of carrying
coordinates around.

Waypoints are stored **per map**. The same name in two maps represents two different places.

---

### <span class="verb get">GET</span> `/waypoints`

List all waypoints stored for a specific map.

#### Request
- **Method**: `GET`
- **Path**: `/waypoints`
- **Query Parameters**:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `map` | `string` | Optional | Map name to query (defaults to current active map) |

- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "map": "workRoom",
  "waypoints": [
    {
      "name": "kitchen",
      "type": "waypoint",
      "x": 1.5,
      "y": -0.4,
      "theta": 0.2
    },
    {
      "name": "charger",
      "type": "dock",
      "x": 0.0,
      "y": 0.0,
      "theta": 0.0
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `map` | `string` | The map these waypoints belong to |
| `waypoints` | `array` | List of waypoint definitions |
| `waypoints[].name` | `string` | Unique waypoint name within this map |
| `waypoints[].type` | `string` | Semantic tag (`"waypoint"`, `"dock"`, `"pickup"`, `"dropoff"`, `"home"`) |
| `waypoints[].x` | `number` | Map X position in metres |
| `waypoints[].y` | `number` | Map Y position in metres |
| `waypoints[].theta` | `number` | Heading orientation in radians |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">404</span> | `map_not_found` | Specified `map` does not exist |

#### Example (cURL)

```bash
# Query waypoints for active map
curl -s $ROBOT/waypoints

# Query waypoints for a specific map
curl -s "$ROBOT/waypoints?map=F2020"
```

---

### <span class="verb post">POST</span> `/waypoints`

Create or replace a waypoint. You can either capture the robot's current localized pose or supply explicit coordinates.

#### Request
- **Method**: `POST`
- **Path**: `/waypoints`
- **Headers**: `Content-Type: application/json`

**Payload:**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | Required | Waypoint identifier (an existing name is replaced) |
| `x` | `number` | Optional | Map X coordinate in metres (must be supplied with `y`) |
| `y` | `number` | Optional | Map Y coordinate in metres (must be supplied with `x`) |
| `theta` | `number` | Optional | Heading angle in radians (default: `0.0`) |
| `type` | `string` | Optional | Semantic tag: `"waypoint"` (default), `"dock"`, `"pickup"`, `"dropoff"`, `"home"` |
| `map` | `string` | Optional | Target map name (defaults to active map) |

```json
{
  "name": "kitchen",
  "x": 1.5,
  "y": -0.4,
  "theta": 0.2,
  "type": "waypoint"
}
```

#### Response
- **Status**: <span class="status ok">201 Created</span>

```json
{
  "waypoint": {
    "name": "kitchen",
    "type": "waypoint",
    "x": 1.5,
    "y": -0.4,
    "theta": 0.2
  },
  "source": "given"
}
```

| Field | Type | Description |
|---|---|---|
| `waypoint` | `object` | Stored waypoint parameters |
| `waypoint.name` | `string` | Waypoint identifier |
| `waypoint.type` | `string` | Tag classification |
| `waypoint.x` | `number` | Stored X coordinate |
| `waypoint.y` | `number` | Stored Y coordinate |
| `waypoint.theta` | `number` | Stored heading angle in radians |
| `source` | `string` | How coordinates were resolved: `"given"` or `"current_pose"` |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">400</span> | `invalid_field` | Empty name, or invalid `type` tag |
| <span class="status err">409</span> | `not_localized` | Pose capture attempted when robot is not localized in map frame |

#### Example (cURL)

```bash
# Option 1: Capture current robot position
curl -s -X POST $ROBOT/waypoints \
     -H 'Content-Type: application/json' \
     -d '{"name": "kitchen"}'

# Option 2: Provide explicit coordinates
curl -s -X POST $ROBOT/waypoints \
     -H 'Content-Type: application/json' \
     -d '{
       "name": "kitchen",
       "x": 1.5,
       "y": -0.4,
       "theta": 0.2
     }'
```

---

### <span class="verb get">GET</span> `/waypoints/{name}`

Retrieve details for a single waypoint by name.

#### Request
- **Method**: `GET`
- **Path**: `/waypoints/{name}`
- **URL Parameters**:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | Required | Waypoint name to retrieve |

- **Query Parameters**:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `map` | `string` | Optional | Map name to query (defaults to current active map) |

- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "waypoint": {
    "name": "kitchen",
    "type": "waypoint",
    "x": 1.5,
    "y": -0.4,
    "theta": 0.2
  }
}
```

| Field | Type | Description |
|---|---|---|
| `waypoint` | `object` | Waypoint record |
| `waypoint.name` | `string` | Waypoint identifier |
| `waypoint.type` | `string` | Semantic classification tag |
| `waypoint.x` | `number` | Position X in metres |
| `waypoint.y` | `number` | Position Y in metres |
| `waypoint.theta` | `number` | Orientation in radians |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">404</span> | `waypoint_not_found` | No waypoint with this name exists in the target map |

#### Example (cURL)

```bash
curl -s $ROBOT/waypoints/kitchen
```

---

### <span class="verb delete">DELETE</span> `/waypoints/{name}`

Delete a single waypoint by name from a map.

#### Request
- **Method**: `DELETE`
- **Path**: `/waypoints/{name}`
- **URL Parameters**:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | Required | Waypoint name to delete |

- **Query Parameters**:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `map` | `string` | Optional | Map name to modify (defaults to current active map) |

- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "deleted": true,
  "name": "kitchen"
}
```

| Field | Type | Description |
|---|---|---|
| `deleted` | `boolean` | `true` when waypoint was successfully removed |
| `name` | `string` | Echo of the removed waypoint name |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">404</span> | `waypoint_not_found` | Waypoint name was not found in the target map |

#### Example (cURL)

```bash
curl -s -X DELETE $ROBOT/waypoints/kitchen
```

---

## Storage

Waypoints persist in a JSON file on the robot, written atomically — a power cut during a
write leaves the previous version intact rather than a truncated file. They survive
reboots, SDK restarts, and app updates.

They are **not** included when you copy a map off the robot. To move a set of waypoints,
`GET /waypoints` on the source robot and `POST` each one to the destination.
