# Recipes

Complete, working answers to the things people actually build.

## Map a new space

```python
from navpromini import NavProMini
import time

robot = NavProMini("navpromini.local")

robot.start_mapping(wait=True)

# Drive it around — teleop, gamepad, or by hand. SLAM does not care how.
for _ in range(4):
    robot.drive(linear=0.15, duration=4.0)
    robot.rotate(1.5708)
    time.sleep(1)

robot.save_map("workRoom")          # <-- before leaving mapping mode
robot.idle(wait=True)
```

!!! danger "Save before switching modes"
    Leaving mapping mode discards everything that session built. The pose graph lives in
    the SLAM process, and stopping the mode stops the process. There is no recovery.

## Set up waypoints

```python
robot.start_navigation("workRoom", wait=True)
robot.localize(0, 0, 0)
robot.wait_for_localization()

# Drive to each spot, then name it.
robot.goto(x=1.5, y=-0.4, wait=True)
robot.save_waypoint("kitchen")

robot.goto(x=3.0, y=0.8, wait=True)
robot.save_waypoint("entrance", type="dropoff")

print([w["name"] for w in robot.waypoints()])
```

Capturing the current pose needs the robot localized — see
[`not_localized`](api/errors.md#409-wrong-state).

## Patrol a route

```python
import time
from navpromini import NavProMini, RobotError

robot = NavProMini("navpromini.local")
route = ["kitchen", "hallway", "entrance"]

while True:
    for stop in route:
        if robot.battery()["percentage"] < 20:
            print("low battery — going to charge")
            robot.dock(wait=True)
            while robot.battery()["percentage"] < 80:
                time.sleep(60)
            continue

        try:
            robot.goto(waypoint=stop, wait=True, timeout=180)
            print(f"reached {stop}")
            time.sleep(5)
        except RobotError as e:
            print(f"could not reach {stop}: {e.code}")
        except TimeoutError:
            print(f"{stop} took too long — cancelling")
            robot.cancel_goal()
```

The robot undocks itself when a goal is sent, so no explicit undock is needed after
charging.

## Charge when low, resume when full

```python
def ensure_charged(robot, resume_at=80, dock_below=20):
    """Dock and wait if the battery is low. Returns True if it charged."""
    if robot.battery()["percentage"] >= dock_below:
        return False

    robot.cancel_goal()
    robot.dock(wait=True)                       # waits for actual charging

    while robot.battery()["percentage"] < resume_at:
        time.sleep(60)
    return True
```

`dock(wait=True)` waits for the battery to report current, not for the robot to stop
moving. A robot stalled against the dock has stopped and is not charging.

## Live dashboard data

=== "Python"

    ```python
    for frame in robot.events(["pose", "battery", "dock_status"]):
        stream, data = frame["stream"], frame.get("data")
        if stream == "pose":
            render_marker(data["x"], data["y"], data["theta"])
        elif stream == "battery":
            render_battery(data["percentage"], data["charging"])
        elif stream == "dock_status":
            render_dock(data)
        elif stream == "error":
            print("stream error:", data["code"], data["message"])
    ```

=== "Browser"

    ```js
    const ws = new WebSocket("ws://navpromini.local:8090/api/v1/events");
    let subscribed = false;

    ws.onopen = () => {
      ws.send(JSON.stringify({
        action: "subscribe",
        streams: ["pose", "battery", "dock_status"],
      }));
      subscribed = true;
    };

    ws.onmessage = (ev) => {
      const { stream, data } = JSON.parse(ev.data);
      switch (stream) {
        case "pose":        renderMarker(data.x, data.y, data.theta); break;
        case "battery":     renderBattery(data.percentage, data.charging); break;
        case "dock_status": renderDock(data); break;
        case "error":       console.error(data.code, data.message); break;
      }
    };

    // Reconnect and re-subscribe: subscriptions live in the connection.
    ws.onclose = () => setTimeout(connect, 2000);
    ```

## Teleop from a gamepad

```python
import time

RATE = 5.0                                   # Hz — commands expire in ~0.5s

while running:
    lx, az = read_gamepad()                  # your input source
    robot.velocity_command(linear=lx * 0.35, angular=az * 1.2)
    time.sleep(1.0 / RATE)

robot.stop()
```

Do not raise the rate much above 5 Hz. Faster does not make the robot smoother — the
expiry window is half a second — and it does add HTTP overhead on a Pi that has other work
to do.

## Health monitoring

```bash
#!/bin/bash
# Alert when a robot is unwell. Suitable for cron.
ROBOT=http://navpromini.local:8090/api/v1

health=$(curl -s --max-time 5 $ROBOT/system/health) || {
    echo "CRITICAL: robot unreachable"; exit 2; }

python3 - "$health" <<'PY'
import json, sys
h = json.loads(sys.argv[1])
bad = [name for name, s in h["sources"].items() if not s["ok"]]
if bad:
    for name in bad:
        s = h["sources"][name]
        age = "never" if s["age_sec"] is None else f"{s['age_sec']:.1f}s ago"
        print(f"WARNING: {name} last published {age} (limit {s['limit_sec']}s)")
    sys.exit(1)
if h["disk"] and h["disk"]["used_percent"] > 90:
    print(f"WARNING: disk {h['disk']['used_percent']}% full"); sys.exit(1)
print(f"OK: all sources fresh, CPU {h['cpu_temperature_c']}°C")
PY
```

Note the health endpoint returns <span class="status ok">200</span> even when unhealthy —
so an unhealthy robot and an unreachable one stay distinguishable, which is the whole point
of monitoring.

## Copy waypoints to another robot

```python
source = NavProMini("robot-a.local")
target = NavProMini("robot-b.local")

for wp in source.waypoints(map_name="workRoom"):
    target.save_waypoint(wp["name"], wp["x"], wp["y"], wp["theta"],
                         type=wp["type"], map_name="workRoom")
```

Only meaningful if both robots use the same map — waypoint coordinates are map-frame, and
two independently-built maps of the same room do not share an origin.

## Poll a fleet

```python
import concurrent.futures as cf

HOSTS = ["robot-a.local", "robot-b.local", "robot-c.local"]

def snapshot(host):
    try:
        r = NavProMini(host, timeout=5)
        b = r.battery()
        return {"host": host, "ok": True,
                "battery": b["percentage"], "charging": b["charging"],
                "mode": r.mode()["mode"]}
    except Exception as e:
        return {"host": host, "ok": False, "error": str(e)}

with cf.ThreadPoolExecutor(max_workers=len(HOSTS)) as pool:
    for row in pool.map(snapshot, HOSTS):
        print(row)
```

Poll in parallel with a short timeout. Serial polling makes total time depend on the
slowest robot, and there is always a slowest robot.

## Shell one-liners

```bash
export ROBOT=http://navpromini.local:8090/api/v1

# Battery percentage
curl -s $ROBOT/state/battery | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["percentage"])'

# Is it charging?
curl -s $ROBOT/dock/status | python3 -c 'import sys,json;print(json.load(sys.stdin)["charging"])'

# Waypoint names
curl -s $ROBOT/waypoints | python3 -c 'import sys,json;print(*[w["name"] for w in json.load(sys.stdin)["waypoints"]],sep="\n")'

# Nearest obstacle, in metres
curl -s $ROBOT/state/scan | python3 -c 'import sys,json;r=[x for x in json.load(sys.stdin)["data"]["ranges"] if x];print(min(r))'

# Stop everything
curl -s -X DELETE $ROBOT/navigation/goal && curl -s -X POST $ROBOT/motion/stop
```

Note the last one: cancelling the goal *and* stopping. `/motion/stop` alone zeroes the
velocity, but the navigation stack keeps issuing its own commands until its goal is
cancelled.
