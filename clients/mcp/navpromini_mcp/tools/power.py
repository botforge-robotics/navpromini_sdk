"""Power management, battery analytics, and autonomous docking MCP tools."""

from typing import Any, Dict
from navpromini import NavProMini, RobotError


def register_power_tools(mcp, robot: NavProMini):
    """Register all power and docking tools on the FastMCP instance."""

    @mcp.tool()
    def dock_robot(
        wait_for_charge: bool = True,
        timeout_sec: int = 300,
    ) -> Dict[str, Any]:
        """Command the robot to return to its charging station, latch, and start charging.
        
        Args:
            wait_for_charge: If True, blocks until the battery enters active charging state.
            timeout_sec: Maximum seconds to allow for docking alignment and latching.
        """
        try:
            res = robot.dock(wait=wait_for_charge, timeout=timeout_sec)
            battery = robot.battery()
            return {
                "success": True,
                "status": "charging" if battery.get("charging") else "docked",
                "battery_percentage": battery.get("percentage"),
                "is_charging": battery.get("charging"),
                "details": res,
            }
        except RobotError as e:
            return {"success": False, "error": f"Docking failed: {e.code} - {e.message}"}
        except TimeoutError:
            return {"success": False, "error": f"Docking timed out after {timeout_sec}s."}

    @mcp.tool()
    def undock_robot() -> Dict[str, Any]:
        """Command the robot to disengage and reverse out of the charging dock."""
        try:
            res = robot.undock()
            return {"success": True, "status": "undocked", "details": res}
        except RobotError as e:
            return {"success": False, "error": f"Undock failed: {e.code} - {e.message}"}

    @mcp.tool()
    def cancel_docking() -> Dict[str, Any]:
        """Abort an in-progress auto-docking alignment sequence immediately."""
        try:
            res = robot.cancel_dock()
            return {"success": True, "message": "Docking sequence cancelled.", "details": res}
        except RobotError as e:
            return {"success": False, "error": f"Cancel dock failed: {e.code} - {e.message}"}

    @mcp.tool()
    def get_power_status() -> Dict[str, Any]:
        """Get comprehensive real-time battery and power metrics."""
        try:
            battery = robot.battery()
            temps = {}
            try:
                temps = robot.temperature()
            except Exception:
                pass

            return {
                "success": True,
                "percentage": battery.get("percentage"),
                "voltage": battery.get("voltage"),
                "current": battery.get("current"),
                "is_charging": battery.get("charging", False),
                "status": battery.get("status", "normal"),
                "battery_temperature_c": temps.get("battery_c"),
                "cpu_temperature_c": temps.get("cpu_c"),
            }
        except RobotError as e:
            return {"success": False, "error": f"{e.code}: {e.message}"}
