# Schedules

An alarm for a [mission](missions.md): pick one, pick a time, pick how it repeats, and the
robot fires it itself — polled on the robot's own SDK process, independent of any app or
client being open or even connected at the moment it's due.

---

### <span class="verb get">GET</span> `/schedules`

```json
{ "schedules": [
  { "id": "morning-run", "mission_id": "morning-patrol", "name": "Morning patrol",
    "hour": 7, "minute": 30, "repeat": "weekly", "date": null,
    "weekdays": [0, 1, 2, 3, 4], "enabled": true }
] }
```

---

### <span class="verb post">POST</span> `/schedules`

Create, or replace by `id` — same create-or-replace-by-id shape as
[`POST /missions`](missions.md).

```bash
curl -s -X POST $ROBOT/schedules -H 'Content-Type: application/json' -d '{
  "id": "morning-run",
  "mission_id": "morning-patrol",
  "name": "Morning patrol",
  "hour": 7, "minute": 30,
  "repeat": "weekly",
  "weekdays": [0, 1, 2, 3, 4]
}'
```

```json
{ "schedule": { "id": "morning-run", "mission_id": "morning-patrol",
                "name": "Morning patrol", "hour": 7, "minute": 30,
                "repeat": "weekly", "date": null,
                "weekdays": [0, 1, 2, 3, 4], "enabled": true } }
```

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Caller-chosen. Resending the same `id` replaces the schedule |
| `mission_id` | yes | Must already exist — [`POST /missions`](missions.md) it first |
| `hour`, `minute` | yes | Integers, 24-hour clock, robot's own local time |
| `repeat` | yes | `once`, `daily`, or `weekly` |
| `date` | if `repeat: "once"` | `YYYY-MM-DD` |
| `weekdays` | if `repeat: "weekly"` | Non-empty list of integers, `0`=Monday .. `6`=Sunday |
| `name` | no | Defaults to empty — display label only, not used to find the schedule |
| `enabled` | no | Default `true`. Set `false` to keep a schedule without it firing |

**Responses**

| | When |
|---|---|
| <span class="status ok">201</span> | Saved |
| <span class="status err">400 `invalid_field`</span> | Missing/malformed field — see the table above |
| <span class="status err">404 `mission_not_found`</span> | `mission_id` doesn't exist |

---

### <span class="verb get">GET</span> `/schedules/{id}`

```json
{ "schedule": { "id": "morning-run", "…": "…" } }
```

<span class="status err">404 `schedule_not_found`</span> if no schedule has that `id`.

---

### <span class="verb delete">DELETE</span> `/schedules/{id}`

```json
{ "deleted": true, "id": "morning-run" }
```

<span class="status err">404 `schedule_not_found`</span> if no schedule has that `id`.

---

## How firing works

There is no separate "run a schedule" endpoint — a due schedule calls exactly the same
internal start path [`POST /missions/{id}/start`](missions.md#post-missionsidstart) uses, so
a scheduled run and a manually-started run are indistinguishable once underway: same
[`GET /missions/status`](missions.md#get-missionsstatus), same
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
