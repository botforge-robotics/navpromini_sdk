---
hide:
  - navigation
---

<div class="npm-hero" markdown>

# NavProMini SDK

Drive, map, navigate and dock a NavProMini robot over plain HTTP.
No ROS installation, no message definitions, no client library required.

<div style="display: flex; gap: 8px; margin-top: 1rem; flex-wrap: wrap;">
  <span style="background: #1565c0; color: white; padding: 3px 10px; border-radius: 4px; font-size: 0.82rem; font-weight: 600;">SDK v1.0.0</span>
  <span style="background: #2e7d32; color: white; padding: 3px 10px; border-radius: 4px; font-size: 0.82rem; font-weight: 600;">REST API v1</span>
  <span style="background: #6a1b9a; color: white; padding: 3px 10px; border-radius: 4px; font-size: 0.82rem; font-weight: 600;">WebSocket v1</span>
  <span style="background: #37474f; color: white; padding: 3px 10px; border-radius: 4px; font-size: 0.82rem; font-weight: 600;">Companion v1.0.0</span>
  <span style="background: #00838f; color: white; padding: 3px 10px; border-radius: 4px; font-size: 0.82rem; font-weight: 600;">GUI App v1.0.0</span>
</div>

</div>

!!! tip "Verify Your Robot &amp; SDK Version"
    You can check the version running on your robot at any time:
    - **In the GUI App**: Open **Settings &rarr; Help &amp; About** or **Settings &rarr; Software Updates**.
    - **Via Terminal / API**: Run `curl http://<robot-ip>:8090/api/v1/system/info` to view `sdk_version` and `api_version`.
    This documentation portal documents **Release v1.0.0 (API v1)**.

```bash
curl http://192.168.1.50:8090/api/v1/state/battery
```

```json
{ "data": { "percentage": 100.0, "voltage": 14.0, "current": 0.1,
            "temperature": 35.0, "status": "full", "charging": true },
  "age_sec": 3.45 }
```

That is the whole learning curve. Everything else is more endpoints in the same shape.

## What this is

NavProMini runs ROS 2 internally. The SDK is a small server that runs **on the robot**
and translates that into an ordinary REST API plus a WebSocket event stream. You get
the robot's real capabilities — telemetry, mapping, navigation, autonomous docking,
direct motion — through an interface any language can call.

<div class="grid cards" markdown>

-   :material-heart-pulse:{ .lg .middle } **Telemetry that admits its age**

    ---

    Every reading carries `age_sec`. A battery value from 40 seconds ago and one from
    40 milliseconds ago are very different facts, and the API says which you have.

    [:octicons-arrow-right-24: State](api/state.md)

-   :material-map-marker-path:{ .lg .middle } **Map, localize, navigate**

    ---

    Build a map with SLAM, save it, activate it, drop named waypoints, then send the
    robot to one by name.

    [:octicons-arrow-right-24: Navigation](api/navigation.md)

-   :material-ev-station:{ .lg .middle } **Autonomous docking**

    ---

    AprilTag visual servoing onto the charging dock. Success is defined as *charging* —
    not as arriving, not as stopping.

    [:octicons-arrow-right-24: Docking](api/docking.md)

-   :material-lightning-bolt:{ .lg .middle } **Push, not poll**

    ---

    Subscribe to the streams you want over one WebSocket. Pose at 10 Hz, battery on
    change, nothing you did not ask for.

    [:octicons-arrow-right-24: Events](api/events.md)

</div>

## Design in three sentences

**Resource-oriented.** Nouns in the path, intent in the verb. `GET /state/battery` reads,
`POST /dock` acts, `DELETE /navigation/goal` cancels. There is no `/cmd/` prefix, because
the HTTP method already says whether something is a command.

**Long operations return immediately.** Docking or crossing a room takes minutes — longer
than any sane HTTP timeout and longer than most proxies allow. Those endpoints answer
<span class="status warn">202</span> the moment the robot *accepts* the goal; progress
comes from the matching status endpoint or the event stream.

**Failures are typed.** Every error is `{"error": {"code", "message", "detail"}}` with a
real status code. Branch on `code`; the prose can improve without breaking your client.

## Get going

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **[Getting started](getting-started.md)**

    Enable the SDK on a robot and make your first five calls.

-   :material-lightbulb-on:{ .lg .middle } **[Core concepts](concepts.md)**

    Modes, coordinate frames, localization, and why some calls return 202.

-   :material-api:{ .lg .middle } **[API reference](reference.html)**

    The full OpenAPI 3.1 specification, rendered.

-   :material-language-python:{ .lg .middle } **[Clients & recipes](clients.md)**

    The Python client, plus curl and JavaScript examples.

</div>

## Status

Version **1.0.0**, API **v1**. Endpoint paths and response shapes under `/api/v1` are
stable: fields may be *added*, never removed or repurposed. Capabilities not yet built —
virtual walls, fixed routes, stored missions — have their namespace reserved and answer
<span class="status err">501</span> rather than <span class="status err">404</span>, so
probing tells you "planned" instead of "typo". See the [roadmap](roadmap.md).
