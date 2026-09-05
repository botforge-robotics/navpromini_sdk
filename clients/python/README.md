# navpromini — Python client

```bash
pip install -e .              # from this directory
pip install -e ".[events]"    # plus the WebSocket event stream
```

### Basic Navigation & Docking

```python
from navpromini import NavProMini

robot = NavProMini("192.168.1.50")

# Telemetry
print("Robot:", robot.info()["robot"]["name"])
print("Battery:", robot.battery()["percentage"], "%")

# Start navigation mode & localize
robot.start_navigation("workRoom", wait=True)
robot.localize(0, 0, 0)
robot.wait_for_localization()

# Send navigation goal and dock
robot.goto(waypoint="kitchen", wait=True)
robot.dock(wait=True)
```

### Missions & Orchestration

```python
# Create a multi-waypoint patrol mission
robot.save_mission({
    "name": "patrol_warehouse",
    "loop": False,
    "tasks": [
        {"waypoint": "station_1", "action": "wait", "params": {"duration_sec": 5}},
        {"waypoint": "station_2", "action": "wait", "params": {"duration_sec": 5}},
        {"waypoint": "dock_spot", "action": "dock"}
    ]
})

# Start & control mission
robot.start_mission("patrol_warehouse")
robot.pause_mission()
robot.resume_mission()

# Wait for completion
status = robot.wait_for_mission(timeout_s=600)
print("Mission result:", status["state"])
```

### Map Images & Schedules

```python
# Fetch active map PNG bytes directly
png_bytes = robot.current_map_image(rotate=0)
with open("map.png", "wb") as f:
    f.write(png_bytes)

# Schedule a daily run with cron
robot.save_schedule({
    "id": "daily_patrol",
    "mission_name": "patrol_warehouse",
    "cron": "0 8 * * *",
    "enabled": True
})
```

Full documentation: <https://botforge-robotics.github.io/navpromini_sdk/clients/>

