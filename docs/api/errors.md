# Errors

Every failure has the same shape:

```json
{ "error": {
    "code": "waypoint_not_found",
    "message": "No waypoint named 'kitchn'",
    "detail": { "waypoint": "kitchn" } } }
```

| Field | Contract |
|---|---|
| `code` | Stable machine-readable slug. **Branch on this** |
| `message` | Human-readable. May change between versions |
| `detail` | Structured context. Always present, sometimes `{}` |

`code` is the stable part. Prose gets improved as we learn what confuses people, and that
should never break a client — so no client should be parsing it.

Unknown paths get this shape too, not Tornado's HTML 404. A client parsing JSON should not
choke precisely when it most needs a readable error: during integration.

## Status codes

| | Meaning |
|---|---|
| <span class="status ok">200</span> | Done |
| <span class="status ok">201</span> | Created |
| <span class="status warn">202</span> | Accepted — the operation is running. Watch its status endpoint |
| <span class="status ok">204</span> | `OPTIONS` preflight |
| <span class="status err">400</span> | The request is wrong. Fix it; retrying will not help |
| <span class="status err">401</span> | Missing or wrong bearer token |
| <span class="status err">404</span> | No such resource, or no such endpoint |
| <span class="status err">409</span> | Right request, wrong moment. Often retryable later |
| <span class="status err">500</span> | Something on the robot failed |
| <span class="status err">501</span> | Reserved for a planned capability |
| <span class="status err">503</span> | A subsystem is not running or has no data yet |
| <span class="status err">504</span> | A ROS call timed out |

## Codes

### 400 — malformed request

| `code` | Cause |
|---|---|
| `invalid_json` | Body is not valid JSON |
| `invalid_body` | Body is valid JSON but not an object |
| `missing_field` | A required field is absent. `detail.missing` lists them |
| `invalid_field` | A field has the wrong type or an unacceptable value |
| `invalid_mode` | `mode` is not `idle`, `mapping` or `navigation` |
| `invalid_name` | A map name contains `/` or starts with `.` |
| `map_required` | Navigation requested with no map, and none previously activated |
| `out_of_range` | A value exceeds a limit. `detail` has `field`, `limit`, `given` |

### 401 — `unauthorized`

Token auth is enabled and the `Authorization: Bearer <token>` header was missing or wrong.
On the WebSocket this is a close with code **4401** rather than a frame.

### 404 — not found

| `code` | Cause |
|---|---|
| `not_found` | No such endpoint. `detail.docs` links here |
| `map_not_found` | No map by that name |
| `waypoint_not_found` | No waypoint by that name **in that map** |
| `no_dock_pose` | The robot has no dock pose set |

### 409 — wrong state

The request was well-formed and would be valid at another time. These are the ones worth
handling deliberately.

| `code` | Cause | What to do |
|---|---|---|
| `mode_busy` | A mode change is already running | Wait, then retry |
| `goal_active` | A navigation goal is running | Cancel, or resend with `replace: true` |
| `goal_rejected` | The navigation stack refused the goal | Check localization and that the target is reachable |
| `dock_busy` | A dock or undock is running | Wait for `/dock/status` to settle |
| `map_exists` | Saving over an existing map | Resend with `overwrite: true` |
| `map_in_use` | Deleting the map navigation is running on | Switch mode first |
| `not_localized` | Capturing a waypoint without a map-frame pose | Localize first, or pass `x`/`y` |

### 500 — robot-side failure

| `code` | Cause |
|---|---|
| `launch_failed` | The mapping or navigation stack refused to start |
| `save_failed` | The map save failed |
| `internal_error` | Unhandled. `message` carries the exception — please report it |

### 501 — `not_implemented`

A reserved namespace: `/zones`, `/routes`, `/missions`. Planned, not built.

```json
{ "error": { "code": "not_implemented",
             "message": "This capability is planned but not available on this robot.",
             "detail": { "path": "/api/v1/zones",
                         "roadmap": "https://botforge-robotics.github.io/navpromini_sdk/roadmap/" } } }
```

These answer `501` rather than `404` so that probing tells you "planned" instead of
"typo". See the [roadmap](../roadmap.md).

### 503 — not available

| `code` | Cause |
|---|---|
| `no_data` | The topic has never published. `detail.source` names it |
| `service_unavailable` | A required ROS service is not running |
| `action_unavailable` | A required action server is not running — usually the wrong mode |

`no_data` almost always means the robot is still starting or a driver failed.
[`GET /system/health`](system.md) says which.

`action_unavailable` on `/navigation/goto` means navigation is not running — check
[`GET /mode`](mode.md) before assuming anything worse.

### 504 — `ros_timeout`

A ROS service or action call did not answer in time. The robot is reachable but a
subsystem is wedged or badly overloaded. Retrying once is reasonable; retrying in a tight
loop is not — it makes an overloaded robot worse.

## Handling them

```python
import requests

def call(method, path, **kw):
    r = requests.request(method, f"{ROBOT}{path}", timeout=10, **kw)
    if r.ok:
        return r.json()
    err = r.json().get("error", {})
    raise RobotError(err.get("code", "unknown"), err.get("message", r.text),
                     err.get("detail", {}), r.status_code)
```

Three rules that cover almost everything:

- **`4xx` other than `409`: do not retry.** The request is wrong; sending it again keeps
  it wrong.
- **`409`: retry after acting.** These are timing conflicts with a specific resolution —
  the table above says which.
- **`503`/`504`: retry with backoff.** A subsystem is starting or busy. Cap the attempts;
  a robot that is down stays down until someone looks at it.
