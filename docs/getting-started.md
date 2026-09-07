# Getting started

!!! tip "Robot not on your network yet?"
    This page assumes a robot that's already powered on and joined to your Wi-Fi. If
    you're setting one up for the first time, start at
    [Robot setup & lifecycle](robot-setup.md) instead.

## 1. Find the robot

Address a robot by **IP and port**: the SDK listens on **8090**.

```
http://<robot-ip>:8090/api/v1
```

The examples below use `192.168.1.50` — substitute your robot's address. Find it from your
router's client list, or on the robot itself with `hostname -I`.

!!! tip "Use the IP, not a `.local` name"
    Robots also answer to `<hostname>.local` over mDNS, but only from the same broadcast
    domain. Across a VPN, a routed subnet, a container, or most Windows setups it will not
    resolve — and the failure looks like the robot being down rather than a name-lookup
    problem. An IP works from anywhere that can route to the robot.

    If the IP moves between reboots, give the robot a DHCP reservation on your router.

Set the base URL environment variable once in your terminal so all commands across the documentation are directly copy-pasteable:

```bash
export ROBOT="http://<robot-ip>:8090/api/v1"
# Example for a robot on your Wi-Fi:
# export ROBOT="http://192.168.1.50:8090/api/v1"
```

Verify reachability and read device metadata:

```bash
curl -s $ROBOT/system/info
```

```json
{
  "robot": { "name": "navpromini", "serial": "46884ab7aa441027", "hostname": "navpromini" },
  "sdk_version": "1.0.0",
  "api_version": "v1",
  "ros_distro": "jazzy",
  "model": "NavProMini",
  "uptime_sec": 812.4,
  "capabilities": {
    "mapping": true, "navigation": true, "docking": true,
    "docking_method": "apriltag", "camera": true,
    "virtual_walls": false, "fixed_routes": false, "missions": true
  }
}
```

!!! tip "Read `capabilities` first"
    It states what this particular unit can do. Adapt to it rather than probing endpoints
    and inferring capability from failures — a `501` and a temporarily broken subsystem
    look very similar from the outside, and only one of them is worth retrying.

## 2. Check it is well

```bash
curl -s $ROBOT/system/health
```

```json
{
  "healthy": true,
  "sources": {
    "odom":            { "ok": true, "age_sec": 0.07, "limit_sec": 2.0 },
    "battery":         { "ok": true, "age_sec": 3.44, "limit_sec": 5.0 },
    "imu":             { "ok": true, "age_sec": 0.07, "limit_sec": 2.0 },
    "lidar":           { "ok": true, "age_sec": 0.12, "limit_sec": 3.0 },
    "cpu_temperature": { "ok": true, "age_sec": 0.90, "limit_sec": 10.0 }
  },
  "cpu_temperature_c": 55.1,
  "disk": { "total_gb": 29.5, "free_gb": 18.2, "used_percent": 35.4 }
}
```

Health is reported **per source**, with the age of the last message and the staleness
limit applied to it. "The robot is unhealthy" is not something you can act on; "lidar last
published 40 seconds ago" is.

## 3. Read some state

=== "curl"

    ```bash
    curl -s $ROBOT/state/battery
    curl -s $ROBOT/state/pose
    curl -s $ROBOT/state/temperature
    ```

=== "Python"

    ```python
    from navpromini import NavProMini

    robot = NavProMini("192.168.1.50")
    print(robot.battery())
    print(robot.pose())
    ```

=== "JavaScript"

    ```js
    const ROBOT = "http://192.168.1.50:8090/api/v1";
    const battery = await (await fetch(`${ROBOT}/state/battery`)).json();
    console.log(battery.data.percentage, battery.data.charging);
    ```

## 4. Make a map

Mapping and navigation both publish the `map → odom` transform, so they are mutually
exclusive. Switching modes always stops the current one first.

```bash
# Start SLAM with a blank map
curl -s -X POST $ROBOT/mode -H 'Content-Type: application/json' \
     -d '{"mode": "mapping"}'
```

Drive the robot around — with the app, a gamepad, or [`/motion/velocity`](api/motion.md) —
then save what it built:

```bash
curl -s -X POST $ROBOT/maps -H 'Content-Type: application/json' \
     -d '{"name": "workRoom"}'
```

The pose graph is serialized alongside the map image, so the map can be **extended** later
rather than only rebuilt from scratch.

## 5. Navigate

```bash
# Switch to navigation on that map
curl -s -X POST $ROBOT/mode -H 'Content-Type: application/json' \
     -d '{"mode": "navigation", "map": "workRoom"}'

# Tell it roughly where it is (accuracy of ±30 cm is plenty — AMCL converges)
curl -s -X POST $ROBOT/navigation/localize -H 'Content-Type: application/json' \
     -d '{"x": 0.0, "y": 0.0, "theta": 0.0}'

# Save the current spot under a name
curl -s -X POST $ROBOT/waypoints -H 'Content-Type: application/json' \
     -d '{"name": "kitchen"}'

# Go there
curl -s -X POST $ROBOT/navigation/goto -H 'Content-Type: application/json' \
     -d '{"waypoint": "kitchen"}'
```

`goto` returns <span class="status warn">202</span> immediately. Watch progress:

```bash
watch -n1 "curl -s $ROBOT/navigation/status"
```

```json
{ "state": "active",
  "target": { "waypoint": "kitchen", "x": 1.5, "y": -0.4, "theta": 0.2 },
  "message": "", "elapsed_sec": 12.4, "distance_remaining": 3.271 }
```

## 6. Send it home to charge

```bash
curl -s -X POST $ROBOT/dock
```

The robot drives to the dock's staging pose, then uses its rear camera and the dock's
AprilTag to centre itself and reverse onto the contacts. Watch `GET /dock/status` until
`charging` is `true` — that is the only proof of contact.

## Enabling the SDK on a robot

Shipped robots run the SDK automatically. On a robot built from source:

```bash
cd ~/NavProMini_ws
colcon build --symlink-install --packages-select navpromini_sdk
source install/setup.bash
ros2 launch navpromini_sdk sdk.launch.py
```

To run it as a service, install the unit shipped with the package:

```bash
sudo cp src/navpromini_sdk/systemd/start_sdk.sh /opt/navpro/scripts/
sudo chmod +x /opt/navpro/scripts/start_sdk.sh
sudo cp src/navpromini_sdk/systemd/navpro-sdk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now navpro-sdk
```

Launch arguments override the defaults in `config/sdk.yaml`:

| Argument | Default | Purpose |
|---|---|---|
| `port` | `8090` | TCP port. Avoids `:80` (provisioning portal), `:8081` (video), `:9090` (rosbridge). |
| `address` | `0.0.0.0` | Bind address. `127.0.0.1` restricts to on-robot clients. |
| `auth_token` | *(empty)* | Bearer token required on every request. Empty disables auth. |

```bash
ros2 launch navpromini_sdk sdk.launch.py port:=8090 auth_token:=s3cret
```

## Authentication

Off by default, so the first request anyone makes works.

!!! danger "Turn it on outside a trusted lab"
    Without a token, anyone who can reach port 8090 can drive the robot. Set `auth_token`
    on any shared or untrusted network.

Once set, pass it as a bearer token:

```bash
curl -s $ROBOT/state/battery -H "Authorization: Bearer s3cret"
```

The WebSocket takes it as a query parameter, since browsers cannot set headers on a
WebSocket handshake:

```
ws://192.168.1.50:8090/api/v1/events?token=s3cret
```

## Coexistence

The SDK is purely additive. rosbridge on `:9090` and the NavProMini app keep working
exactly as before, and both can be used at the same time as the SDK.
