# NavProMini SDK

**HTTP + WebSocket control and telemetry API for the NavProMini AMR.**

[![Docs](https://img.shields.io/badge/docs-navpromini__sdk-3949ab)](https://botforge-robotics.github.io/navpromini_sdk/)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1-00897b)](openapi.yaml)
[![License](https://img.shields.io/badge/license-MIT-informational)](LICENSE)

Drive, map, navigate and dock a NavProMini over plain HTTP. No ROS installation, no
message definitions, no client library required.

```bash
curl http://192.168.1.50:8090/api/v1/state/battery
```

```json
{ "data": { "percentage": 100.0, "voltage": 14.0, "current": 0.1,
            "temperature": 35.0, "status": "full", "charging": true },
  "age_sec": 3.45 }
```

📖 **[Full documentation →](https://botforge-robotics.github.io/navpromini_sdk/)**

---

## What is here

| Path | Contents |
|---|---|
| [`openapi.yaml`](openapi.yaml) | OpenAPI 3.1 specification — the source of truth |
| [`docs/`](docs/) | Documentation site (MkDocs Material) |
| [`clients/python/`](clients/python/) | Python client |
| [`examples/`](examples/) | Runnable curl, Python and browser examples |

The **server** lives on the robot, in the `navpromini_sdk` ROS 2 package inside the
[Nav_Pro_Mini](https://github.com/botforge-robotics/Nav_Pro_Mini) workspace. This repo is
what an integrator needs; that repo is what the robot runs.

## Quick start

```bash
export ROBOT=http://192.168.1.50:8090/api/v1

curl -s $ROBOT/system/info                    # identity and capabilities
curl -s $ROBOT/system/health                  # per-subsystem freshness
curl -s $ROBOT/state/pose                     # where it is

curl -s -X POST $ROBOT/navigation/goto \
     -H 'Content-Type: application/json' \
     -d '{"waypoint": "kitchen"}'             # send it somewhere

curl -s -X POST $ROBOT/dock                   # send it home to charge
```

Python:

```bash
pip install -e clients/python
```

```python
from navpromini import NavProMini

robot = NavProMini("192.168.1.50")
robot.start_navigation("workRoom", wait=True)
robot.localize(0, 0, 0)
robot.wait_for_localization()
robot.goto(waypoint="kitchen", wait=True)
robot.dock(wait=True)
```

## The API in one table

| Group | Endpoints |
|---|---|
| **System** | `GET /system/info`, `/system/health` |
| **State** | `GET /state/pose`, `/velocity`, `/battery`, `/imu`, `/scan`, `/temperature` |
| **Mode** | `GET /mode`, `POST /mode` — idle / mapping / navigation |
| **Maps** | `GET /maps`, `POST /maps`, `GET /maps/current`, `DELETE /maps/{name}`, `POST /maps/{name}/activate` |
| **Waypoints** | `GET`/`POST /waypoints`, `GET`/`DELETE /waypoints/{name}` |
| **Navigation** | `POST /navigation/goto`, `GET /navigation/status`, `DELETE /navigation/goal`, `POST /navigation/localize`, `GET /navigation/path` |
| **Docking** | `POST /dock`, `POST /undock`, `GET /dock/status`, `GET`/`PUT /dock/pose` |
| **Motion** | `POST /motion/velocity`, `/move`, `/rotate`, `/stop` |
| **Events** | `WS /events` — subscribe to pose, battery, scan, dock status and more |

## Design

**Resource-oriented.** Nouns in the path, intent in the HTTP verb. `GET /state/battery`
reads, `POST /dock` acts, `DELETE /navigation/goal` cancels. There is no `/cmd/` prefix,
because the method already says whether something is a command.

**Long operations return immediately.** Docking or crossing a room takes minutes — longer
than any sane HTTP timeout. Those endpoints answer `202 Accepted` when the robot *accepts*
the goal; progress comes from the matching status endpoint or the event stream.

**Failures are typed.** Every error is `{"error": {"code", "message", "detail"}}` with a
real status code. Branch on `code`; prose can improve without breaking clients.

**Readings admit their age.** Every state response carries `age_sec`. A battery value from
40 seconds ago and one from 40 milliseconds ago are different facts, and the API says which
you have. A source that never published returns `503`, not zeros.

**Additive versioning.** Under `/api/v1`, fields may be added — never removed or
repurposed. Reserved namespaces (`/zones`, `/routes`, `/missions`) answer `501`, so probing
tells you "planned" rather than "typo".

## Security

Bearer-token auth is available and **off by default**, so the first request anyone makes
works.

> ⚠️ On any network that is not a trusted lab, set `auth_token`. Without it, anyone who can
> reach port 8090 can drive the robot.

```bash
ros2 launch navpromini_sdk sdk.launch.py auth_token:=s3cret
curl -s $ROBOT/state/battery -H "Authorization: Bearer s3cret"
```

## Building the docs

```bash
pip install mkdocs-material
mkdocs serve            # http://127.0.0.1:8000
mkdocs gh-deploy        # publish to GitHub Pages
```

## License

MIT — see [LICENSE](LICENSE).
