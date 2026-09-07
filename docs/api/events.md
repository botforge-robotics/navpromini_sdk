# Events

One WebSocket, push updates, no polling interval to tune.

```bash
# Connect via wscat or websocat using your $ROBOT environment variable:
wscat -c "ws://${ROBOT#http://}/events"
```

Address directly:

```
ws://<robot-ip>:8090/api/v1/events
```

With authentication enabled, pass the token as a query parameter — browsers cannot set
headers on a WebSocket handshake:

```bash
wscat -c "ws://${ROBOT#http://}/events?token=s3cret"
```

## Protocol

Deliberately small. Three client actions, one server frame shape.

```json
// client → server
{ "action": "subscribe",   "streams": ["pose", "battery"] }
{ "action": "unsubscribe", "streams": ["pose"] }
{ "action": "ping" }

// server → client
{ "stream": "battery", "data": { "percentage": 100.0, "charging": true }, "ts": 1755782411.83 }
```

Every server frame has `stream`, `ts` (Unix seconds, float), and — except for `pong` —
`data`.

**Subscription is opt-in.** Nothing arrives until you ask for it. Pose at 10 Hz would swamp
a client that only wanted battery, over WiFi that is not always generous.

## On connect

```json
{ "stream": "hello",
  "data": { "streams": ["battery", "cpu_temperature", "dock_status", "dock_tag",
                        "imu", "path", "pose", "pose_odom", "scan", "velocity"],
            "api_version": "v1" },
  "ts": 1755782400.11 }
```

The `hello` frame lists what this robot can stream. Read it rather than hardcoding the
list — a newer robot may offer more.

## Subscribing

```json
→ { "action": "subscribe", "streams": ["pose", "battery"] }
← { "stream": "subscribed", "data": { "streams": ["battery", "pose"] }, "ts": … }
```

The confirmation carries your **complete** subscription set, not just what you added — so a
client that lost track can resynchronize from it.

## Streams

<div class="md-typeset__table" markdown>

| Stream | Max rate | Payload |
|---|---|---|
| `pose` | 10 Hz | `{x, y, theta, frame}` — map frame, only while localized |
| `pose_odom` | 10 Hz | `{x, y, theta, frame}` — odom frame, always available |
| `velocity` | 10 Hz | `{linear, angular}` |
| `battery` | on change | Same shape as [`/state/battery`](state.md) |
| `imu` | 5 Hz | `{orientation, angular_velocity, linear_acceleration}` |
| `scan` | 2 Hz | Same shape as [`/state/scan`](state.md) |
| `path` | 2 Hz | `[{x, y}, …]` — the planned route |
| `dock_status` | on change | Docking controller state string |
| `dock_tag` | 5 Hz | `{visible, id, offset_px, size_px, bearing_rad, skew}` |
| `cpu_temperature` | on change | Number, °C |

</div>

Rates are **ceilings, not schedules**. A stream is only sent when its source publishes; if
the lidar stops, `scan` stops. Streams marked "on change" have no throttle because their
sources publish slowly already.

`pose` versus `pose_odom` is the same distinction as in [`/state/pose`](state.md): `pose`
is map-frame and only flows while the robot is localized, `pose_odom` always flows but
means nothing between sessions. Subscribe to `pose_odom` too if you need continuity through
a localization dropout.

`dock_tag` is diagnostic — it exposes what the docking camera currently sees. `offset_px`
is how far the tag is from image centre, `bearing_rad` the angle to it, `skew` how
off-square the approach is. Useful for tuning or explaining a failed dock; not something a
normal application needs.

## Keepalive

```json
→ { "action": "ping" }
← { "stream": "pong", "ts": 1755782415.02 }
```

Send a ping every 20–30 seconds on a long-lived connection. Not for the robot's benefit —
for the NAT tables and proxies in between, which drop idle connections without telling
either end.

## Errors

Stream errors arrive as frames, not as a closed socket:

```json
{ "stream": "error",
  "data": { "code": "unknown_stream",
            "message": "Unknown stream(s): batery",
            "detail": { "valid": ["battery", "cpu_temperature", "…"] } },
  "ts": … }
```

| `code` | Cause |
|---|---|
| `invalid_json` | The message was not JSON |
| `invalid_action` | `action` was not `subscribe`, `unsubscribe` or `ping` |
| `invalid_streams` | `streams` was not a list |
| `unknown_stream` | A name is not in the `hello` list — `detail.valid` has the real ones |

A bad request does not close the connection. Subscribing to three valid streams and one
typo rejects **the whole request**, so fix the typo and resend rather than assuming the
valid three went through.

Authentication failure is the exception: the socket closes with code **4401**
(`unauthorized`) before anything else happens.

## Example

=== "Python"

    ```python
    import json, websockets, asyncio

    async def watch():
        url = "ws://192.168.1.50:8090/api/v1/events"
        async with websockets.connect(url) as ws:
            print(json.loads(await ws.recv())["data"]["streams"])   # hello

            await ws.send(json.dumps({"action": "subscribe",
                                      "streams": ["pose", "battery"]}))
            async for raw in ws:
                frame = json.loads(raw)
                if frame["stream"] == "pose":
                    d = frame["data"]
                    print(f"{d['x']:.2f}, {d['y']:.2f}  ({d['frame']})")
                elif frame["stream"] == "battery":
                    print(f"battery {frame['data']['percentage']}%")

    asyncio.run(watch())
    ```

=== "JavaScript"

    ```js
    const ws = new WebSocket("ws://192.168.1.50:8090/api/v1/events");

    ws.onopen = () => ws.send(JSON.stringify({
      action: "subscribe", streams: ["pose", "battery"],
    }));

    ws.onmessage = (ev) => {
      const { stream, data } = JSON.parse(ev.data);
      if (stream === "pose")    updateMarker(data.x, data.y, data.theta);
      if (stream === "battery") updateBadge(data.percentage, data.charging);
      if (stream === "error")   console.error(data.code, data.message);
    };

    setInterval(() => {
      if (ws.readyState === WebSocket.OPEN)
        ws.send(JSON.stringify({ action: "ping" }));
    }, 25000);
    ```

=== "websocat"

    ```bash
    echo '{"action":"subscribe","streams":["battery"]}' \
      | websocat -n ws://192.168.1.50:8090/api/v1/events
    ```

## Reconnecting

The socket drops when the robot restarts, when WiFi blips, or when a proxy times out. A
client should reconnect with backoff and **re-subscribe** — subscriptions live in the
connection and are gone with it.

Nothing is buffered while you are away. On reconnect you get the current value of each
stream as it next publishes, not a replay. For state you cannot miss, read the REST
endpoint once after reconnecting and continue from there.

## Load

Each client gets its own throttling, so five dashboards do not multiply the robot's
publishing work — they multiply the sending work, which is much cheaper. Still, `scan` at
2 Hz is a few hundred kilobytes a minute per subscriber. Subscribe to what you render.
