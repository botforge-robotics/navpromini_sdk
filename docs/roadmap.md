# Roadmap

Three namespaces are reserved and answer <span class="status err">501
`not_implemented`</span> rather than <span class="status err">404</span>. They are
documented here so an integrator can see the intended shape now — and so that probing an
endpoint tells you "planned" rather than "you made a typo".

!!! warning "Shapes below are provisional"
    Everything under `/api/v1` that is *implemented* is stable. The sketches on this page
    are not: they will change before they ship. Do not build against them.

## Reserved now

### `/zones` — virtual walls and speed zones

Regions drawn on a map that constrain where and how fast the robot moves: keep-out areas
around a staircase, slow zones near a doorway, preferred-direction lanes in a corridor.

```jsonc
// sketch, not implemented
POST /api/v1/zones
{ "name": "stairwell", "type": "keepout",
  "polygon": [[1.2, 0.4], [2.8, 0.4], [2.8, 1.9], [1.2, 1.9]] }
```

Planned types: `keepout`, `speed_limit`, `preferred_direction`.

### `/routes` — fixed routes

An ordered list of waypoints the robot follows as a unit, instead of the caller sending
each goal and waiting. Useful for patrols and delivery loops, where the sequence is fixed
and the client should not have to stay connected to drive it.

```jsonc
// sketch, not implemented
POST /api/v1/routes
{ "name": "patrol",
  "waypoints": ["kitchen", "hallway", "entrance"],
  "loop": true }

POST /api/v1/routes/patrol/start
```

### `/missions` — scripted sequences

Routes with actions in between: go somewhere, wait, capture an image, call an external
service, then move on. The NavProMini app already builds and runs these; the reserved
namespace is for exposing the same thing to non-app clients.

```jsonc
// sketch, not implemented
POST /api/v1/missions
{ "name": "inspection",
  "steps": [
    { "type": "goto",    "waypoint": "kitchen" },
    { "type": "wait",    "seconds": 5 },
    { "type": "capture", "camera": "front" },
    { "type": "goto",    "waypoint": "entrance" },
    { "type": "dock" }
  ] }
```

## Also under consideration

- **Camera access** — a still-image endpoint. The robot already streams video on port 8081;
  this would put a single frame behind the same API and auth as everything else.
- **Map images** — `GET /maps/{name}/image` returning the occupancy grid as PNG, so a
  client can draw a map without parsing `.pgm`.
- **Multi-robot discovery** — finding every NavProMini on a network from one call, for
  fleet clients that currently have to scan.
- **Webhooks** — a POST to your URL on selected events, for integrations that cannot hold
  a WebSocket open.

No dates. These land when they are solid on the robot, not before.

## Compatibility

The rule for `/api/v1` is **additive only**: new endpoints and new fields, never a removed
or repurposed one. Ignore fields you do not recognize and your client keeps working.

Anything that cannot be done additively would go to `/api/v2`, served alongside `v1` rather
than replacing it. There is no plan for a v2.

## Asking for something

Open an issue at
[github.com/botforge-robotics/navpromini_sdk](https://github.com/botforge-robotics/navpromini_sdk/issues).
What the robot needs to *do* is more useful than a proposed endpoint — the shape is the
easy part, and knowing the real task usually changes it.
