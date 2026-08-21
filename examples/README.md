# Examples

Runnable scripts against a live robot. Set the host first:

```bash
export ROBOT_HOST=navpromini.local     # or the IP
export ROBOT_TOKEN=                    # only if the robot has auth enabled
```

| File | What it does |
|---|---|
| `quickstart.sh` | Every read-only endpoint, with curl. Safe on any robot |
| `patrol.py` | Drives a waypoint loop, docking to charge when low |
| `watch_events.py` | Prints frames from the WebSocket stream |
| `teleop.py` | Arrow-key teleop from a terminal |
| `dashboard.html` | Single-file browser dashboard — open it, no server needed |

Python examples need the client:

```bash
pip install -e ../clients/python[events]
```
