# navpromini — Python client

```bash
pip install -e .              # from this directory
pip install -e ".[events]"    # plus the WebSocket event stream
```

```python
from navpromini import NavProMini

robot = NavProMini("navpromini.local")

print(robot.info()["robot"]["name"])
print(robot.battery()["percentage"])

robot.start_navigation("workRoom", wait=True)
robot.localize(0, 0, 0)
robot.wait_for_localization()

robot.goto(waypoint="kitchen", wait=True)
robot.dock(wait=True)
```

Full documentation: <https://botforge-robotics.github.io/navpromini_sdk/clients/>
