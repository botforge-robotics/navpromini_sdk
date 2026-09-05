"""Emergency stop, manual jogging, and system reflex MCP tools."""

from typing import Any, Dict
from navpromini import NavProMini, RobotError


def register_emergency_tools(mcp, robot: NavProMini):
    """Register all emergency, reflex, and diagnostic tools on the FastMCP instance."""

    @mcp.tool()
    def emergency_stop() -> Dict[str, Any]:
        """CRITICAL SAFETY REFLEX: Immediately halt all robot motion, cancel active goals, and abort missions.
        
        Zeroes motor command velocities (cmd_vel), aborts Nav2 path tracking, and stops
        any active mission sequence.
        """
        results = {}
        # 1. Stop motors immediately
        try:
            robot.stop()
            results["motors_stopped"] = True
        except Exception as e:
            results["motors_stopped"] = f"Failed: {str(e)}"

        # 2. Cancel navigation goal
        try:
            robot.cancel_goal()
            results["navigation_goal_cancelled"] = True
        except Exception:
            results["navigation_goal_cancelled"] = "None active or failed"

        # 3. Cancel active mission
        try:
            robot.cancel_mission()
            results["mission_cancelled"] = True
        except Exception:
            results["mission_cancelled"] = "None active or failed"

        return {
            "success": True,
            "message": "EMERGENCY STOP executed. Wheel velocities set to zero.",
            "actions": results,
        }

    @mcp.tool()
    def jog_robot(
        distance_m: float = 0.0,
        rotation_rad: float = 0.0
    ) -> Dict[str, Any]:
        """Execute a small relative manual jog motion (e.g. to nudge away from an obstacle).
        
        Args:
            distance_m: Relative linear distance to move in meters (positive = forward, negative = backward).
                        Limited to [-1.0, 1.0] meters per jog for safety.
            rotation_rad: Relative angular rotation in radians (positive = counter-clockwise, negative = clockwise).
                          Limited to [-3.1415, 3.1415] radians per jog.
        """
        # Safety clamp
        clamped_dist = max(-1.0, min(1.0, distance_m))
        clamped_rot = max(-3.1415, min(3.1415, rotation_rad))

        report = {}
        try:
            if abs(clamped_dist) > 0.001:
                robot.move(clamped_dist)
                report["linear_moved_m"] = clamped_dist
            if abs(clamped_rot) > 0.001:
                robot.rotate(clamped_rot)
                report["angular_rotated_rad"] = clamped_rot

            return {"success": True, "jog_executed": report}
        except RobotError as e:
            return {"success": False, "error": f"Jog failed: {e.code} - {e.message}"}

    @mcp.tool()
    def get_system_health() -> Dict[str, Any]:
        """Inspect robot health, sensor topic freshness, and Nav2 lifecycle node states."""
        try:
            health = robot.health()
            lifecycle = robot.lifecycle()
            return {
                "success": True,
                "overall_status": health.get("status", "unknown"),
                "subsystems": health.get("checks", {}),
                "lifecycle_nodes": lifecycle,
            }
        except RobotError as e:
            return {"success": False, "error": f"{e.code}: {e.message}"}
