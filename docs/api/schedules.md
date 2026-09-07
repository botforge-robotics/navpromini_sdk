# Schedules

An alarm for a [mission](missions.md): pick one, pick a time, pick how it repeats, and the
robot fires it itself — polled on the robot's own SDK process, independent of any app or
client being open or even connected at the moment it's due.

---

### <span class="verb get">GET</span> `/schedules`

List all active and configured schedules.

#### Request
- **Method**: `GET`
- **Path**: `/schedules`
- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "schedules": [
    {
      "id": "morning-run",
      "mission_id": "morning-patrol",
      "name": "Morning patrol",
      "hour": 7,
      "minute": 30,
      "repeat": "weekly",
      "date": null,
      "weekdays": [0, 1, 2, 3, 4],
      "enabled": true
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `schedules` | `array` | List of configured schedule objects |
| `schedules[].id` | `string` | Unique identifier for the schedule |
| `schedules[].mission_id` | `string` | ID of the mission to execute when triggered |
| `schedules[].name` | `string` | Human-readable label for display |
| `schedules[].hour` | `integer` | Hour of the day (0-23, robot local time) |
| `schedules[].minute` | `integer` | Minute of the hour (0-59, robot local time) |
| `schedules[].repeat` | `string` | Frequency: `"once"`, `"daily"`, or `"weekly"` |
| `schedules[].date` | `string \| null` | Date string (`YYYY-MM-DD`) if `repeat: "once"`, otherwise `null` |
| `schedules[].weekdays` | `array[integer]` | List of weekdays (`0`=Monday .. `6`=Sunday) if `repeat: "weekly"` |
| `schedules[].enabled` | `boolean` | `true` if active; `false` if paused or self-disabled after one-time run |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">500</span> | `internal_error` | Failed to load schedules from disk storage |

#### Example (cURL)

```bash
curl -s $ROBOT/schedules
```

---

### <span class="verb post">POST</span> `/schedules`

Create a new schedule or replace an existing schedule by `id`.

#### Request
- **Method**: `POST`
- **Path**: `/schedules`
- **Headers**: `Content-Type: application/json`

**Payload:**

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | Required | Caller-chosen unique identifier. Resending replaces the schedule |
| `mission_id` | `string` | Required | Must already exist — [`POST /missions`](missions.md) it first |
| `hour` | `integer` | Required | Hour of day (0-23, robot local time) |
| `minute` | `integer` | Required | Minute of hour (0-59, robot local time) |
| `repeat` | `string` | Required | Frequency: `"once"`, `"daily"`, or `"weekly"` |
| `date` | `string` | Conditional | Required if `repeat: "once"`. Format: `YYYY-MM-DD` |
| `weekdays` | `array[integer]` | Conditional | Required if `repeat: "weekly"`. Non-empty list of integers, `0`=Monday .. `6`=Sunday |
| `name` | `string` | Optional | Human-readable display label |
| `enabled` | `boolean` | Optional | Default `true`. Set `false` to keep schedule without it firing |

```json
{
  "id": "morning-run",
  "mission_id": "morning-patrol",
  "name": "Morning patrol",
  "hour": 7,
  "minute": 30,
  "repeat": "weekly",
  "weekdays": [0, 1, 2, 3, 4],
  "enabled": true
}
```

#### Response
- **Status**: <span class="status ok">201 Created</span>

```json
{
  "schedule": {
    "id": "morning-run",
    "mission_id": "morning-patrol",
    "name": "Morning patrol",
    "hour": 7,
    "minute": 30,
    "repeat": "weekly",
    "date": null,
    "weekdays": [0, 1, 2, 3, 4],
    "enabled": true
  }
}
```

| Field | Type | Description |
|---|---|---|
| `schedule` | `object` | The saved schedule record |
| `schedule.id` | `string` | Unique identifier of the schedule |
| `schedule.mission_id` | `string` | Associated mission ID |
| `schedule.name` | `string` | Display name |
| `schedule.hour` | `integer` | Hour of execution |
| `schedule.minute` | `integer` | Minute of execution |
| `schedule.repeat` | `string` | Frequency type |
| `schedule.date` | `string \| null` | Target date or null |
| `schedule.weekdays` | `array[integer]` | Selected weekdays |
| `schedule.enabled` | `boolean` | Active state |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">400</span> | `invalid_field` | Missing or malformed required fields |
| <span class="status err">404</span> | `mission_not_found` | The target `mission_id` does not exist |

#### Example (cURL)

```bash
curl -s -X POST $ROBOT/schedules \
     -H 'Content-Type: application/json' \
     -d '{
       "id": "morning-run",
       "mission_id": "morning-patrol",
       "name": "Morning patrol",
       "hour": 7,
       "minute": 30,
       "repeat": "weekly",
       "weekdays": [0, 1, 2, 3, 4]
     }'
```

---

### <span class="verb get">GET</span> `/schedules/{id}`

Retrieve a single schedule configuration by its unique ID.

#### Request
- **Method**: `GET`
- **Path**: `/schedules/{id}`
- **URL Parameters**:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | Required | Unique schedule identifier |

- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "schedule": {
    "id": "morning-run",
    "mission_id": "morning-patrol",
    "name": "Morning patrol",
    "hour": 7,
    "minute": 30,
    "repeat": "weekly",
    "date": null,
    "weekdays": [0, 1, 2, 3, 4],
    "enabled": true
  }
}
```

| Field | Type | Description |
|---|---|---|
| `schedule` | `object` | The schedule record |
| `schedule.id` | `string` | Schedule ID |
| `schedule.mission_id` | `string` | Mission ID |
| `schedule.name` | `string` | Display label |
| `schedule.hour` | `integer` | Hour |
| `schedule.minute` | `integer` | Minute |
| `schedule.repeat` | `string` | Repeat frequency |
| `schedule.date` | `string \| null` | Date string if one-time run |
| `schedule.weekdays` | `array[integer]` | Target weekday indices |
| `schedule.enabled` | `boolean` | Enabled status |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">404</span> | `schedule_not_found` | No schedule exists with the given `id` |

#### Example (cURL)

```bash
curl -s $ROBOT/schedules/morning-run
```

---

### <span class="verb delete">DELETE</span> `/schedules/{id}`

Delete a configured schedule by ID.

#### Request
- **Method**: `DELETE`
- **Path**: `/schedules/{id}`
- **URL Parameters**:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | Required | Unique schedule identifier |

- **Headers**: None required
- **Payload**: None

#### Response
- **Status**: <span class="status ok">200 OK</span>

```json
{
  "deleted": true,
  "id": "morning-run"
}
```

| Field | Type | Description |
|---|---|---|
| `deleted` | `boolean` | `true` when schedule was removed |
| `id` | `string` | Echo of deleted schedule ID |

#### Error Codes

| Status | Code | Cause / Resolution |
|---|---|---|
| <span class="status err">404</span> | `schedule_not_found` | No schedule exists with the given `id` |

#### Example (cURL)

```bash
curl -s -X DELETE $ROBOT/schedules/morning-run
```

---

## How firing works

There is no separate "run a schedule" endpoint — a due schedule calls exactly the same
internal start path [`POST /missions/{id}/start`](missions.md) uses, so
a scheduled run and a manually-started run are indistinguishable once underway: same
[`GET /missions/status`](missions.md), same
[event stream](events.md) entries.

!!! warning "Skipped, not queued — like a phone alarm, not a job scheduler"
    Two situations cause a due schedule to be silently skipped rather than deferred:

    - **Another mission is already running or paused.** The scheduled one does not
      interrupt it, and does not wait for it to finish — it is simply not started this
      time. Watch for a `schedule.skipped` event with `"reason": "mission_active"` if this
      matters to you.
    - **The SDK process was not running when the minute passed** — rebooting, or the
      service was stopped. There is no catch-up on restart: a missed alarm stays missed,
      exactly like a phone alarm silenced by a dead battery, rather than firing late the
      moment the robot comes back.

A `repeat: "once"` schedule disables itself (`enabled` flips to `false`) the moment it
fires — the same self-terminating behaviour a phone's one-time alarm has, rather than
sitting there permanently matching a date that has already passed. A schedule whose
`mission_id` no longer resolves (the mission was deleted) disables itself the same way,
with a `schedule.skipped` event carrying `"reason": "mission_not_found"`, instead of
failing silently on every check forever.
