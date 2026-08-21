# Clients

Any HTTP client works — the API is plain JSON over HTTP. What follows is the maintained
Python client, and idiomatic starting points for other languages.

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
they are. The only real additions are the `wait=` helpers, because polling for a terminal
state is the one piece of boilerplate every caller would otherwise write — and get subtly
wrong.

### Reading state

State methods unwrap `data` and return the reading directly:

```python
robot.battery()      # {"percentage": 100.0, "voltage": 14.0, "charging": True, …}
robot.velocity()     # {"linear": 0.0, "angular": 0.0}
robot.temperature()  # {"cpu_c": 55.1, "battery_c": 35.0}
robot.is_charging()  # True
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

No package to install; `fetch` is enough.

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

  battery() { return this.call("GET", "/state/battery").then((r) => r.data); }
  pose()    { return this.call("GET", "/state/pose"); }
  goto(waypoint) { return this.call("POST", "/navigation/goto", { waypoint }); }
  dock()    { return this.call("POST", "/dock"); }
  stop()    { return this.call("POST", "/motion/stop"); }
}
```

CORS is open on the robot, so this works from a browser page served anywhere. See
[Events](api/events.md) for the WebSocket half.

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

## Generating a client

The [OpenAPI specification](reference.html) is the source of truth, and generating from it
beats hand-writing for any language you do not want to maintain by hand:

```bash
curl -O https://botforge-robotics.github.io/navpromini_sdk/openapi.yaml

# any OpenAPI 3.1 generator, e.g.
openapi-generator-cli generate -i openapi.yaml -g typescript-fetch -o ./client
```

The spec is also served by the robot's docs URL, so a client can be generated against the
exact version a given robot runs rather than against the published one.

---

## curl

For scripts and for debugging, curl is often the right answer:

```bash
export ROBOT=http://192.168.1.50:8090/api/v1

curl -s $ROBOT/state/battery | python3 -m json.tool

curl -s -X POST $ROBOT/navigation/goto \
     -H 'Content-Type: application/json' \
     -d '{"waypoint": "kitchen"}'
```

With auth enabled:

```bash
curl -s $ROBOT/state/battery -H "Authorization: Bearer $TOKEN"
```

More in [Recipes](recipes.md).
