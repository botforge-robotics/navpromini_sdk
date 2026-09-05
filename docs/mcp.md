# Model Context Protocol (MCP) Server

The **Model Context Protocol (MCP)** server connects the NavPro Mini AMR to modern AI agents (Google Antigravity, Claude Desktop, Cursor, and custom Python agent frameworks). It allows Large Language Models (LLMs) to reason about the robot's physical environment, synthesize multi-stop missions, monitor live telemetry, and control physical movement.

Operates purely over **standard JSON-RPC via Stdio or SSE** — no heavy Vision-Language-Action (VLA) neural policies or local GPU hardware required.

---

## Installation

```bash
pip install -e clients/mcp
```

This installs the `navpromini-mcp` CLI executable and the `navpromini_mcp` Python module.

---

## Quickstart

Run the server directly using standard I/O (default):

```bash
navpromini-mcp --host 192.168.1.50 --port 8090
```

Or run it as a network-accessible Server-Sent Events (SSE) server on port 8091:

```bash
navpromini-mcp --host 192.168.1.50 --transport sse --sse-port 8091
```

---

## AI Agent Setup

### Antigravity Integration

Add the server to your project's `.agents/mcp_config.json` or global `~/.gemini/config/mcp_config.json`:

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

### Claude Desktop Integration

Add to `claude_desktop_config.json`:

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

## Core Capabilities

### 1. Mission Synthesis & Feasibility

AI agents can synthesize complex multi-stop missions from natural language instructions. The server automatically:
- Checks that all waypoints exist in the active map.
- Computes transit distances and estimated duration.
- Evaluates **battery consumption feasibility** to ensure the AMR will not run out of power mid-patrol.

```python
# Example MCP Tool Invocation: synthesize_and_save_mission
{
  "name": "warehouse_inspection",
  "description": "Inspect aisles 1 and 2, then return to dock",
  "loop": false,
  "tasks": [
    {"waypoint": "aisle_1", "action": "wait", "params": {"duration_sec": 10}},
    {"waypoint": "aisle_2", "action": "wait", "params": {"duration_sec": 15}},
    {"waypoint": "charging_dock", "action": "dock"}
  ]
}
```

### 2. Runtime Mission Control & Scheduling

- `execute_mission(mission_name, wait_for_completion=True)`: Start mission execution.
- `control_active_mission(action="pause" | "resume" | "cancel")`: Intervene in real-time.
- `schedule_recurring_mission(schedule_id, mission_name, cron="0 8 * * *")`: Automate routines with standard 5-field cron syntax.

### 3. Safety Interlocks & Emergency Stop

- **Low-Battery Interlock**: Inbound requests reject navigation tasks if battery $<15\%$ unless the target is a charging dock. If battery $<8\%$, a critical dock order is enforced.
- **Emergency Stop Reflex (`emergency_stop`)**: Instantly zeroes wheel motor command velocities, cancels Nav2 goals, and halts active missions.
- **AMCL Global Relocalization (`trigger_global_relocalization`)**: Disperses particles and performs a 360° LiDAR sweep to re-localize when tracking is lost.

---

## Context Resources

Passive read-only feeds that agents can inspect without mutating robot state:

| Resource URI | Description |
|---|---|
| `robot://telemetry` | Real-time canonical state JSON (battery, pose, velocities, safety status). |
| `robot://waypoints` | Semantic waypoint catalog defined in the current map. |
| `robot://missions/library` | Catalog of all saved missions stored on the robot. |
| `robot://missions/active` | Current task index, progress percentage, and execution status. |
| `robot://system/health` | Nav2 lifecycle states and sensor topic freshness. |

---

## Agent Prompts (Runbooks)

The server exposes built-in prompt runbooks:
- `facility_patrol_planner`: Guides the model to inspect waypoints, query operational constraints, compile a mission DAG, verify battery budget, and attach a cron schedule.
- `robot_fault_recovery`: Step-by-step diagnostic and recovery runbook for navigation failures, obstacle traps, and lost localization.
- `preflight_safety_audit`: Pre-shift hardware, sensor, and battery checklist.
