# API overview

Base URL:

```
http://<robot-ip>:8090/api/v1
```

Examples on these pages use `192.168.1.50` as the robot's address — substitute your own.

JSON in, JSON out. `Content-Type: application/json` on any request with a body.

## Every endpoint

<div class="md-typeset__table" markdown>

| | Endpoint | Purpose |
|---|---|---|
| <span class="verb get">GET</span> | `/system/info` | Identity, version, capabilities |
| <span class="verb get">GET</span> | `/system/health` | Per-subsystem freshness and disk |
| <span class="verb get">GET</span> | `/state/pose` | Position and heading |
| <span class="verb get">GET</span> | `/state/velocity` | Measured linear and angular speed |
| <span class="verb get">GET</span> | `/state/battery` | Charge, voltage, current, charging |
| <span class="verb get">GET</span> | `/state/imu` | Orientation, angular rate, acceleration |
| <span class="verb get">GET</span> | `/state/scan` | Laser scan |
| <span class="verb get">GET</span> | `/state/temperature` | CPU and battery temperature |
| <span class="verb get">GET</span> | `/mode` | Current mode |
| <span class="verb post">POST</span> | `/mode` | Switch to idle / mapping / navigation |
| <span class="verb get">GET</span> | `/maps` | List saved maps |
| <span class="verb post">POST</span> | `/maps` | Save the map being built |
| <span class="verb get">GET</span> | `/maps/current` | Which map is in use |
| <span class="verb delete">DELETE</span> | `/maps/{name}` | Delete a map |
| <span class="verb post">POST</span> | `/maps/{name}/activate` | Switch navigation to this map |
| <span class="verb get">GET</span> | `/waypoints` | List waypoints for a map |
| <span class="verb post">POST</span> | `/waypoints` | Create or replace a waypoint |
| <span class="verb get">GET</span> | `/waypoints/{name}` | Read one waypoint |
| <span class="verb delete">DELETE</span> | `/waypoints/{name}` | Delete a waypoint |
| <span class="verb post">POST</span> | `/navigation/goto` | Send a goal |
| <span class="verb get">GET</span> | `/navigation/status` | Goal progress |
| <span class="verb delete">DELETE</span> | `/navigation/goal` | Cancel the active goal |
| <span class="verb post">POST</span> | `/navigation/localize` | Seed the pose estimate |
| <span class="verb get">GET</span> | `/navigation/path` | Current planned path |
| <span class="verb post">POST</span> | `/dock` | Dock autonomously |
| <span class="verb post">POST</span> | `/undock` | Leave the dock and stop |
| <span class="verb get">GET</span> | `/dock/status` | Docking state and charging |
| <span class="verb get">GET</span> | `/dock/pose` | Where the dock is |
| <span class="verb put">PUT</span> | `/dock/pose` | Set where the dock is |
| <span class="verb post">POST</span> | `/motion/velocity` | Continuous velocity command |
| <span class="verb post">POST</span> | `/motion/move` | Drive a fixed distance |
| <span class="verb post">POST</span> | `/motion/rotate` | Rotate in place |
| <span class="verb post">POST</span> | `/motion/stop` | Stop now |
| <span class="verb ws">WS</span> | `/events` | Subscribe to live streams |

</div>

## Conventions

**Units are SI, always.** Metres, metres per second, radians, radians per second, seconds,
degrees Celsius, volts, amps. Angles are counter-clockwise-positive, with zero along the
map's +X axis. Percentages are 0–100.

**`theta` instead of quaternions.** The robot drives on a floor, so a single heading angle
carries everything a quaternion would, without four numbers and a normalization rule.

**`null` means "no value".** Never zero. Sensor readings can be NaN or infinite — JSON can
represent neither, so non-finite values are emitted as `null` rather than as output a
strict parser rejects.

**Additive versioning.** Under `/api/v1`, fields may be added but never removed or
repurposed. Ignore fields you do not recognize.

**CORS is open.** A browser dashboard can call the robot directly. The robot is a LAN
device with no cookie-based session, so there is no CSRF surface for an origin check to
protect; when token auth is enabled it travels in a header, which browsers will not attach
cross-origin by accident.

**`OPTIONS` returns <span class="status ok">204</span>** on every route, for preflight.

## Reading the pages

Each endpoint shows its request and a real response captured from a robot. Where behaviour
is surprising, the page says *why* it is that way — those notes are the parts worth reading
before writing an integration, not after debugging one.

For the machine-readable contract, use the [OpenAPI specification](../reference.html) —
generate a client from it rather than hand-writing one.
