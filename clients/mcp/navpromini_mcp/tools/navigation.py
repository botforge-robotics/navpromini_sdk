"""Navigation, waypoint goto, and AMCL relocalization MCP tools."""

from typing import Any, Dict, Optional
from navpromini import NavProMini, RobotError
from navpromini_mcp.config import config
from navpromini_mcp.guardrails import check_preflight_safety, SafetyInterlockError


def register_navigation_tools(mcp, robot: NavProMini):
    """Register all navigation-related tools on the FastMCP instance."""

    @mcp.tool()
    def navigate_to_waypoint(
        waypoint: str,
        wait_for_arrival: bool = True,
        timeout_sec: int = config.default_nav_timeout_sec,
        replace_active_goal: bool = True,
    ) -> Dict[str, Any]:
        """Navigate the robot to a named waypoint using Nav2 path planning and obstacle avoidance.
        
        Args:
            waypoint: Name of the destination waypoint (e.g. 'kitchen', 'station_2', 'charging_dock').
            wait_for_arrival: If True (recommended), blocks until arrival, returning success or failure reason.
            timeout_sec: Maximum seconds to allow for navigation before aborting.
            replace_active_goal: If True, cancels any in-progress goal and proceeds with the new one.
        """
        is_dock = "dock" in waypoint.lower()
        try:
            check_preflight_safety(robot, is_dock_destination=is_dock)
        except SafetyInterlockError as err:
            return {"success": False, "error": str(err)}

        try:
            res = robot.goto(
                waypoint=waypoint,
                wait=wait_for_arrival,
                timeout=timeout_sec,
                replace=replace_active_goal,
            )
            return {
                "success": True,
                "destination": waypoint,
                "status": "reached" if wait_for_arrival else "goal_accepted",
                "details": res,
            }
        except RobotError as e:
            return {"success": False, "error": f"Navigation failed: {e.code} - {e.message}"}
        except TimeoutError:
            try:
                robot.cancel_goal()
            except Exception:
                pass
            return {
                "success": False,
                "error": f"Navigation to '{waypoint}' timed out after {timeout_sec}s. Goal was cancelled."
            }

    @mcp.tool()
    def navigate_to_coordinates(
        x: float,
        y: float,
        yaw: float = 0.0,
        wait_for_arrival: bool = True,
        timeout_sec: int = config.default_nav_timeout_sec,
        replace_active_goal: bool = True,
    ) -> Dict[str, Any]:
        """Navigate the robot to arbitrary (x, y, yaw) coordinates in the map frame.
        
        Args:
            x: Target X position in meters.
            y: Target Y position in meters.
            yaw: Target heading angle in radians (-3.1415 to +3.1415).
            wait_for_arrival: If True, blocks until the robot reaches the pose.
            timeout_sec: Maximum seconds to allow for navigation before aborting.
            replace_active_goal: If True, replaces any active navigation goal.
        """
        try:
            check_preflight_safety(robot)
        except SafetyInterlockError as err:
            return {"success": False, "error": str(err)}

        try:
            res = robot.goto(
                x=x,
                y=y,
                yaw=yaw,
                wait=wait_for_arrival,
                timeout=timeout_sec,
                replace=replace_active_goal,
            )
            return {
                "success": True,
                "target_coordinates": {"x": x, "y": y, "yaw": yaw},
                "status": "reached" if wait_for_arrival else "goal_accepted",
                "details": res,
            }
        except RobotError as e:
            return {"success": False, "error": f"Navigation failed: {e.code} - {e.message}"}
        except TimeoutError:
            try:
                robot.cancel_goal()
            except Exception:
                pass
            return {
                "success": False,
                "error": f"Navigation to ({x}, {y}) timed out after {timeout_sec}s. Goal was cancelled."
            }

    @mcp.tool()
    def cancel_navigation_goal() -> Dict[str, Any]:
        """Cancel the active navigation goal and immediately stop robot path tracking."""
        try:
            res = robot.cancel_goal()
            return {"success": True, "message": "Navigation goal cancelled.", "details": res}
        except RobotError as e:
            return {"success": False, "error": f"{e.code}: {e.message}"}

    @mcp.tool()
    def get_navigation_status() -> Dict[str, Any]:
        """Get live Nav2 navigation goal status, progress, and remaining distance."""
        try:
            status = robot.navigation_status()
            return {"success": True, "status": status}
        except RobotError as e:
            return {"success": False, "error": f"{e.code}: {e.message}"}

    @mcp.tool()
    def trigger_global_relocalization() -> Dict[str, Any]:
        """Recover localization when the robot is lost.
        
        Disperses AMCL particles uniformly across the map space and rotates in place
        to let the 2D LiDAR integrate environment geometry.
        """
        try:
            robot.global_relocalize()
            # Perform slow 360-degree rotation to observe surrounding obstacles
            robot.rotate(6.283)
            pose = robot.pose()
            return {
                "success": True,
                "message": "AMCL particles dispersed and 360° scan sweep executed.",
                "current_pose": pose,
            }
        except RobotError as e:
            return {"success": False, "error": f"Relocalization failed: {e.code} - {e.message}"}

    @mcp.tool()
    def set_initial_pose(x: float, y: float, yaw: float = 0.0) -> Dict[str, Any]:
        """Seed AMCL with an initial pose estimate (2D Pose Estimate).
        
        Args:
            x: Estimated X coordinate in meters.
            y: Estimated Y coordinate in meters.
            yaw: Estimated heading orientation in radians.
        """
        try:
            res = robot.localize(x=x, y=y, yaw=yaw)
            return {"success": True, "estimated_pose": {"x": x, "y": y, "yaw": yaw}, "details": res}
        except RobotError as e:
            return {"success": False, "error": f"Failed setting initial pose: {e.code} - {e.message}"}
