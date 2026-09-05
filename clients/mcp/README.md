# NavPro Mini MCP Server (`navpromini-mcp`)

The **Model Context Protocol (MCP)** server for the NavPro Mini AMR. Enables Large Language Models (LLMs) and autonomous AI agents (such as Google Antigravity, Claude Desktop, Cursor, or custom agent frameworks) to directly monitor, navigate, and orchestrate the physical robot.

Operates **purely via symbolic JSON-RPC tools and context resources** — no heavy Vision-Language-Action (VLA) neural policies or GPU overhead required.

---

## Features

- **Mission Synthesis & Validation**: Dynamically design, simulate, compile, and execute multi-waypoint missions with automatic battery consumption feasibility checks.
- **Safety Interlocks & Guardrails**: Automatic low-battery interlock (<15% blocks non-docking tasks, <8% critical dock command), waypoint existence verification, and instant emergency stop reflex.
- **Autonomous Docking**: Complete charge lifecycle control (`dock_robot`, `undock_robot`, `cancel_docking`, `get_power_status`).
- **Spatial Topology & Relocalization**: Inspect active maps, manage waypoints, and trigger AMCL global particle dispersion if lost.
- **Passive Context Resources**: Read real-time telemetry (`robot://telemetry`), waypoints (`robot://waypoints`), and active missions (`robot://missions/active`) without side effects.
- **Pre-packaged Runbook Prompts**: Reusable agent prompts (`facility_patrol_planner`, `robot_fault_recovery`, `preflight_safety_audit`).

---

## Installation

```bash
# Inside clients/mcp directory
pip install -e .

# Or from repository root
pip install -e clients/mcp
```

---

## Configuration & Agent Setup

### 1. Antigravity Configuration

Add the server to your project or global Antigravity MCP config:
- Project: `.agents/mcp_config.json`
- Global: `~/.gemini/config/mcp_config.json`

```json
{
  "mcpServers": {
    "navpromini": {
      "command": "navpromini-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "NAVPRO_ROBOT_HOST": "192.168.1.50",
        "NAVPRO_ROBOT_PORT": "8090",
        "NAVPRO_ROBOT_TOKEN": ""
      }
    }
  }
}
```

### 2. Claude Desktop Configuration

In `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `~/.config/Claude/claude_desktop_config.json` (Linux):

```json
{
  "mcpServers": {
    "navpromini": {
      "command": "python3",
      "args": ["-m", "navpromini_mcp", "--transport", "stdio"],
      "env": {
        "NAVPRO_ROBOT_HOST": "192.168.1.50"
      }
    }
  }
}
```

---

## Tool Reference

### Mission Orchestration
| Tool | Description |
|---|---|
| `synthesize_and_save_mission` | Validates waypoint existence, checks battery budget, and saves a multi-task mission. |
| `execute_mission` | Starts a saved mission with optional synchronous completion waiting. |
| `control_active_mission` | Runtime intervention: `pause`, `resume`, `cancel`. |
| `get_mission_status` | Returns active mission task index, progress, and state. |
| `list_missions` | Lists all saved missions stored on the robot. |
| `schedule_recurring_mission` | Attaches a standard cron schedule to a mission (e.g. `0 8 * * *`). |
| `list_schedules` | Lists all active recurring cron schedules. |

### Navigation & Spatial
| Tool | Description |
|---|---|
| `navigate_to_waypoint` | Drives robot to a named landmark using Nav2 obstacle avoidance. |
| `navigate_to_coordinates` | Drives robot to arbitrary $(x, y, \theta)$ map coordinates. |
| `cancel_navigation_goal` | Aborts active navigation immediately. |
| `get_navigation_status` | Returns Nav2 goal state and distance remaining. |
| `trigger_global_relocalization` | Disperses AMCL particles and rotates 360° to recover lost pose. |
| `set_initial_pose` | Seeds AMCL with an initial pose estimate $(x, y, \theta)$. |
| `list_waypoints` | Lists all semantic landmarks in the active map. |
| `save_current_location_as_waypoint` | Captures current localized position as a named waypoint. |
| `get_active_map_info` | Active map resolution, width, height, and origin. |
| `list_available_maps` | Lists saved maps on the robot. |
| `switch_active_map` | Loads a saved map into the navigation stack. |

### Power & Safety
| Tool | Description |
|---|---|
| `dock_robot` | Returns to charging dock, aligns, latches, and verifies charging state. |
| `undock_robot` | Disengages from charging contacts and backs away. |
| `cancel_docking` | Aborts an in-progress docking sequence. |
| `get_power_status` | Comprehensive battery metrics (%, voltage, current, temps). |
| `emergency_stop` | **Critical Reflex**: Instantly zeroes wheel velocities, cancels goals and missions. |
| `jog_robot` | Manual relative nudge (linear meters, angular rotation). |
| `get_system_health` | Node lifecycle states and sensor topic freshness. |

---

## Resources & Prompts

### Context Resources
- `robot://telemetry`: Real-time canonical state JSON (battery, pose, velocity, mode).
- `robot://waypoints`: Known waypoints in the active map.
- `robot://missions/library`: Catalog of saved missions.
- `robot://missions/active`: Live execution state of in-flight mission.
- `robot://system/health`: Subsystem health and Nav2 lifecycle nodes.

### Built-in Agent Prompts
- `facility_patrol_planner`: Guided workflow to inspect waypoints, calculate battery budgets, synthesize missions, and attach cron schedules.
- `robot_fault_recovery`: Triage runbook for navigation failures, obstacle traps, or lost localization.
- `preflight_safety_audit`: Pre-shift hardware, sensor, and battery verification checklist.
