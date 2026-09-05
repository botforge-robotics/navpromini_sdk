"""MCP Resource providers for read-only robot telemetry and state feeds."""

import json
from navpromini import NavProMini


def register_resources(mcp, robot: NavProMini):
    """Register all read-only resource URIs on the FastMCP instance."""

    @mcp.resource("robot://telemetry")
    def get_telemetry_resource() -> str:
        """Canonical real-time robot telemetry: battery, pose, velocities, safety status."""
        try:
            state = robot.robot_state()
        except Exception as e:
            state = {"error": f"Failed reading canonical robot state: {str(e)}"}
        return json.dumps(state, indent=2)

    @mcp.resource("robot://waypoints")
    def get_waypoints_resource() -> str:
        """Active map waypoint library and semantic coordinates."""
        try:
            wps = robot.waypoints()
        except Exception as e:
            wps = {"error": f"Failed reading waypoints: {str(e)}"}
        return json.dumps(wps, indent=2)

    @mcp.resource("robot://missions/library")
    def get_missions_library_resource() -> str:
        """Catalog of all saved missions stored on the robot."""
        try:
            missions = robot.missions()
        except Exception as e:
            missions = {"error": f"Failed reading missions library: {str(e)}"}
        return json.dumps(missions, indent=2)

    @mcp.resource("robot://missions/active")
    def get_active_mission_resource() -> str:
        """Live progress and execution state of the active mission."""
        try:
            status = robot.mission_status()
        except Exception as e:
            status = {"error": f"Failed reading mission status: {str(e)}"}
        return json.dumps(status, indent=2)

    @mcp.resource("robot://system/health")
    def get_system_health_resource() -> str:
        """Subsystem health, sensor freshness, and Nav2 lifecycle states."""
        try:
            health = robot.health()
        except Exception as e:
            health = {"error": f"Failed reading health: {str(e)}"}
        return json.dumps(health, indent=2)
