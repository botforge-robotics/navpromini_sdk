# Clients

Any HTTP client works — the API is plain JSON over HTTP. What follows is the maintained
Python client, idiomatic manual starting points, and an in-depth guide to generating strongly-typed
client libraries for any language directly from the OpenAPI specification.

## Python

```bash
pip install -e clients/python              # from a clone of this repo
pip install -e "clients/python[events]"    # plus the WebSocket stream
```

```python
from navpromini import NavProMini

robot = NavProMini("192.168.1.50")          # port 8090, no auth
# robot = NavProMini("192.168.0.129", token="s3cret")

print(robot.info()["robot"]["name"])
print(robot.battery())
print(robot.pose())
```

The client is deliberately thin: one method per endpoint, the server's field names kept as
they are. The only additions are the `wait=` helpers, because polling for a terminal
state is the one piece of boilerplate every caller would otherwise write — and get subtly
wrong.

### Reading state

State methods unwrap `data` and return the reading directly:

```python
robot.battery()      # {"percentage": 100.0, "voltage": 14.0, "charging": True, …}
robot.velocity()     # {"linear": 0.0, "angular": 0.0}
robot.temperature()  # {"cpu_c": 55.1, "battery_c": 35.0}
robot.is_charging()  # True
robot.robot_state()  # Canonical unified status: nav, battery, dock, safety
robot.lifecycle()    # Nav2 managed node states (lifecycle manager, planner, etc.)
```

`pose()` folds `localized` and `age_sec` into the returned dict, because a pose without
them is easy to misuse:

```python
p = robot.pose()
if not p["localized"]:
    raise RuntimeError("odom-frame pose — not comparable to map coordinates")
```

When you need the age of any other reading, use `state_raw()`:

```python
robot.state_raw("scan")   # {"data": {…}, "age_sec": 0.12}
```

### Waiting

```python
robot.start_navigation("workRoom", wait=True)   # until the mode has settled
robot.wait_for_localization()                   # until pose is map-frame
robot.goto(waypoint="kitchen", wait=True)       # until arrival, raises on failure
robot.dock(wait=True)                           # until the battery is charging
robot.wait_for_mission(timeout_s=600)           # until active mission completes
```

`goto(wait=True)` raises `RobotError` when the goal ends in `failed` or `canceled`, so a
drive that did not happen cannot be mistaken for one that did. Every wait helper raises
`TimeoutError` at its deadline rather than blocking forever.

### Driving

```python
robot.drive(linear=0.15, duration=3.0)      # forward 3s, then stop
robot.drive(angular=0.5, duration=1.0)      # turn left 1s
robot.move(0.4)                             # forward 40cm
robot.move(-0.2)                            # back 20cm
robot.rotate(1.5708)                        # 90° counter-clockwise
robot.stop()
```

`drive()` repeats the velocity command at 5 Hz for you, because a single command expires
after half a second. It stops on the way out, including if the block raises.

### Missions & Orchestration

Missions group multiple waypoints and actions into repeatable autonomous workflows.

```python
# 1. Define and save a multi-stop patrol mission
patrol_mission = {
    "name": "morning_inspection",
    "description": "Inspect warehouse stations 1 and 2",
    "loop": False,
    "tasks": [
        {"waypoint": "station_1", "action": "wait", "params": {"duration_sec": 5}},
        {"waypoint": "station_2", "action": "wait", "params": {"duration_sec": 10}},
        {"waypoint": "dock_entry", "action": "dock"}
    ]
}
robot.save_mission(patrol_mission)

# 2. Start execution
robot.start_mission("morning_inspection")

# 3. Check status or pause / resume
status = robot.mission_status()
print(f"Mission state: {status['state']}, task {status.get('current_task_index')}")

robot.pause_mission()    # Pause execution (e.g. during manual operator intervention)
robot.resume_mission()   # Resume where it left off

# 4. Wait synchronously until mission finishes
final_status = robot.wait_for_mission(timeout_s=900)
print(f"Mission finished with result: {final_status['state']}")
```

To abort an in-flight mission:
```python
robot.cancel_mission()
```

### Automated Schedules

Run missions automatically at scheduled times using standard cron expressions:

```python
# Create or update a schedule
robot.save_schedule({
    "id": "daily_cleaning",
    "mission_name": "morning_inspection",
    "cron": "0 8 * * *",      # Every day at 08:00 AM
    "enabled": True
})

# List active schedules
for sched in robot.schedules():
    print(f"[{sched['id']}] runs mission '{sched['mission_name']}' on cron '{sched['cron']}'")

# Remove a schedule
robot.delete_schedule("daily_cleaning")
```

### Active Maps & Binary Image Export

Retrieve map metadata or fetch rendered map images directly as binary bytes:

```python
# Get metadata (resolution, dimensions, origin)
info = robot.current_map_info()
print(f"Map resolution: {info['resolution']} m/px, size: {info['width']}x{info['height']}")

# Fetch ready-to-render PNG image bytes (optionally rotate 0, 90, 180, 270 deg)
png_bytes = robot.current_map_image(rotate=0)
with open("current_map.png", "wb") as f:
    f.write(png_bytes)

# Fetch raw RGB565 binary bytes (useful for embedded screens or microcontrollers)
rgb_bytes = robot.current_map_raw()
```

### Relocalization & Dock Cancellation

```python
# Trigger AMCL global re-localization particles dispersal if the robot is lost
robot.global_relocalize()

# Abort an in-progress auto-docking maneuver
robot.cancel_dock()
```

### Errors

```python
from navpromini import NavProMini, RobotError

try:
    robot.goto(waypoint="kitchen")
except RobotError as e:
    if e.code == "goal_active":
        robot.goto(waypoint="kitchen", replace=True)
    elif e.code == "waypoint_not_found":
        print("known waypoints:", [w["name"] for w in robot.waypoints()])
    else:
        raise
```

`RobotError` carries `code`, `message`, `detail` and `status`. Branch on `code` — see the
[error reference](api/errors.md).

### Events

```python
for frame in robot.events(["pose", "battery"]):
    if frame["stream"] == "pose":
        print(frame["data"])
```

A generator over the [event socket](api/events.md). It yields every frame, including
`hello` and `error` — a caller that never sees an error frame cannot react to a rejected
subscription.

---

## JavaScript / TypeScript

### Minimal Browser / Node Fetch Client

No package required; standard `fetch` is sufficient:

```js
class NavProMini {
  constructor(host, { port = 8090, token = null } = {}) {
    this.base = `http://${host}:${port}/api/v1`;
    this.headers = { "Content-Type": "application/json" };
    if (token) this.headers.Authorization = `Bearer ${token}`;
  }

  async call(method, path, body) {
    const res = await fetch(this.base + path, {
      method,
      headers: this.headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    const json = res.status === 204 ? {} : await res.json();
    if (!res.ok) {
      const e = json.error ?? {};
      throw Object.assign(new Error(e.message ?? res.statusText),
                          { code: e.code, detail: e.detail, status: res.status });
    }
    return json;
  }

  battery()        { return this.call("GET", "/state/battery").then((r) => r.data); }
  pose()           { return this.call("GET", "/state/pose"); }
  goto(waypoint)   { return this.call("POST", "/navigation/goto", { waypoint }); }
  dock()           { return this.call("POST", "/dock"); }
  cancelDock()     { return this.call("DELETE", "/dock"); }
  startMission(id) { return this.call("POST", `/missions/${id}/start`); }
  pauseMission(id) { return this.call("POST", `/missions/${id}/pause`); }
  resumeMission(id){ return this.call("POST", `/missions/${id}/resume`); }
  cancelMission(id){ return this.call("POST", `/missions/${id}/cancel`); }
  stop()           { return this.call("POST", "/motion/stop"); }
}
```

CORS is open on the robot, so this works from web apps, dashboards, or Electron applications.

---

## Go

```go
type Client struct {
    Base  string
    Token string
    HTTP  *http.Client
}

func (c *Client) Get(path string, out any) error {
    req, _ := http.NewRequest("GET", c.Base+path, nil)
    if c.Token != "" {
        req.Header.Set("Authorization", "Bearer "+c.Token)
    }
    res, err := c.HTTP.Do(req)
    if err != nil {
        return err
    }
    defer res.Body.Close()
    if res.StatusCode >= 400 {
        var e struct {
            Error struct{ Code, Message string } `json:"error"`
        }
        json.NewDecoder(res.Body).Decode(&e)
        return fmt.Errorf("%s: %s", e.Error.Code, e.Error.Message)
    }
    return json.NewDecoder(res.Body).Decode(out)
}
```

---

## Generating Client Libraries

Because [`openapi.yaml`](openapi.yaml) adheres strictly to the **OpenAPI 3.0** standard, you can automatically generate strongly-typed, production-ready SDKs for **over 50 programming languages and frameworks** using [OpenAPI Generator](https://openapi-generator.tech/).

### 1. Where to Get the Specification

You can generate against the repository spec, the online hosted spec, or directly against a live robot:

```bash
# Option A: From this repository
openapi.yaml

# Option B: From GitHub Pages
curl -O https://botforge-robotics.github.io/navpromini_sdk/openapi.yaml

# Option C: Directly from a live robot (matches exact firmware version)
curl -O http://192.168.1.50:8090/api/v1/openapi.yaml
```

### 2. Install OpenAPI Generator

Choose any convenient installation method:

=== "npm (Recommended)"
    ```bash
    npm install -g @openapitools/openapi-generator-cli
    ```

=== "Docker"
    ```bash
    # No installation needed — run directly via Docker:
    docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli generate \
      -i /local/openapi.yaml ...
    ```

=== "Homebrew (macOS / Linux)"
    ```bash
    brew install openapi-generator
    ```

=== "Standalone JAR"
    ```bash
    curl -O https://repo1.maven.org/maven2/org/openapitools/openapi-generator-cli/7.3.0/openapi-generator-cli-7.3.0.jar
    java -jar openapi-generator-cli-7.3.0.jar generate -i openapi.yaml ...
    ```

---

### 3. Generation Commands & Code Examples by Language

#### A. TypeScript / JavaScript (Node.js & Web)

Generates strongly-typed models, request parameter interfaces, and an Axios-based client:

```bash
openapi-generator-cli generate \
  -i openapi.yaml \
  -g typescript-axios \
  -o clients/typescript \
  --additional-properties=npmName=@botforge/navpromini-sdk,supportsES6=true,withSeparateModelsAndApi=true
```

**Usage in your TypeScript project:**
```typescript
import { Configuration, NavigationApi, StateApi, MissionsApi } from "@botforge/navpromini-sdk";

const config = new Configuration({
  basePath: "http://192.168.1.50:8090/api/v1",
  // accessToken: "s3cret" // if authentication is enabled
});

const stateApi = new StateApi(config);
const navApi = new NavigationApi(config);
const missionsApi = new MissionsApi(config);

// Read battery
const battery = await stateApi.getStateBattery();
console.log(`Battery: ${battery.data.data?.percentage}%`);

// Send navigation goal
await navApi.postNavigationGoto({
  navigationGotoRequest: { waypoint: "kitchen" }
});

// Start mission
await missionsApi.postMissionsNameStart({ name: "morning_inspection" });
```

*(For pure browser `fetch` without Axios, use `-g typescript-fetch` instead).*

---

#### B. Go

Generates an idiomatic Go module with struct tags, error unwrapping, and context support:

```bash
openapi-generator-cli generate \
  -i openapi.yaml \
  -g go \
  -o clients/go \
  --additional-properties=packageName=navpromini,isGoSubmodule=true
```

**Usage in your Go project:**
```go
package main

import (
    "context"
    "fmt"
    nav "github.com/botforge-robotics/navpromini_sdk/clients/go"
)

func main() {
    cfg := nav.NewConfiguration()
    cfg.Servers = nav.ServerConfigurations{
        {URL: "http://192.168.1.50:8090/api/v1"},
    }
    client := nav.NewAPIClient(cfg)

    // Check battery
    batteryResp, _, err := client.StateAPI.GetStateBattery(context.Background()).Execute()
    if err != nil {
        panic(err)
    }
    fmt.Printf("Battery: %.1f%%\n", *batteryResp.Data.Percentage)

    // Navigate to waypoint
    gotoReq := *nav.NewNavigationGotoRequest()
    gotoReq.SetWaypoint("kitchen")
    _, _, err = client.NavigationAPI.PostNavigationGoto(context.Background()).NavigationGotoRequest(gotoReq).Execute()
    if err != nil {
        fmt.Printf("Nav error: %v\n", err)
    }
}
```

---

#### C. Rust

Generates a modern `reqwest` + `tokio` async client with `serde` models:

```bash
openapi-generator-cli generate \
  -i openapi.yaml \
  -g rust \
  -o clients/rust \
  --additional-properties=packageName=navpromini
```

**Usage in `Cargo.toml` / `main.rs`:**
```rust
use navpromini::apis::configuration::Configuration;
use navpromini::apis::state_api;
use navpromini::apis::navigation_api;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut config = Configuration::new();
    config.base_path = "http://192.168.1.50:8090/api/v1".to_string();

    let battery = state_api::get_state_battery(&config).await?;
    println!("Battery percentage: {:?}", battery.data.percentage);

    Ok(())
}
```

---

#### D. Dart / Flutter (Mobile & Tablet Dashboards)

Generates a [Dio](https://pub.dev/packages/dio) based client ideal for Flutter apps:

```bash
openapi-generator-cli generate \
  -i openapi.yaml \
  -g dart-dio \
  -o clients/dart \
  --additional-properties=pubName=navpromini_sdk
```

**Usage in Flutter:**
```dart
import 'package:navpromini_sdk/navpromini_sdk.dart';

final api = NavprominiSdk(basePathOverride: 'http://192.168.1.50:8090/api/v1');

// Get state
final battery = await api.getStateApi().getStateBattery();
print('Battery: ${battery.data?.data?.percentage}%');

// Trigger auto-docking
await api.getDockingApi().postDock();
```

---

#### E. C++ (Qt or Native Embedded)

Generates client classes using Microsoft's Casablanca `cpprest` or CPR:

```bash
openapi-generator-cli generate \
  -i openapi.yaml \
  -g cpp-restsdk \
  -o clients/cpp
```

---

#### F. C# / .NET (Unity / WPF)

```bash
openapi-generator-cli generate \
  -i openapi.yaml \
  -g csharp \
  -o clients/csharp \
  --additional-properties=packageName=Botforge.NavProMini
```

---

### 4. Customizing Generated Clients

- **Ignore generated files**: Add a `.openapi-generator-ignore` file in your output directory (similar to `.gitignore`) to prevent custom edits (like custom helper methods or unit tests) from being overwritten during re-generation.
- **List all supported generators**:
  ```bash
  openapi-generator-cli list
  ```
- **Inspect generator options**:
  ```bash
  openapi-generator-cli config-help -g <generator-name>
  ```

---

## curl

For shell scripts and rapid terminal debugging, curl is often the easiest tool:

```bash
export ROBOT=http://192.168.1.50:8090/api/v1

# Read telemetry
curl -s $ROBOT/state/battery | jq .
curl -s $ROBOT/state/pose | jq .

# Send robot to waypoint
curl -s -X POST $ROBOT/navigation/goto \
     -H 'Content-Type: application/json' \
     -d '{"waypoint": "kitchen"}'

# Pause active mission
curl -s -X POST $ROBOT/missions/morning_inspection/pause

# Download map image
curl -s $ROBOT/maps/current/image -o current_map.png
```

With authentication enabled:

```bash
curl -s $ROBOT/state/battery -H "Authorization: Bearer $TOKEN"
```

More in [Recipes](recipes.md).
