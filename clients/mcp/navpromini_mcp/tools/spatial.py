"""Spatial topology, maps, and waypoint MCP tools."""

from typing import Any, Dict, List, Optional
from navpromini import NavProMini, RobotError


def register_spatial_tools(mcp, robot: NavProMini):
    """Register all spatial and map-related tools on the FastMCP instance."""

    @mcp.tool()
    def list_waypoints() -> Dict[str, Any]:
        """List all named waypoints and landmarks saved in the active map.
        
        Returns waypoints with their name, type ('dock', 'pickup', 'patrol', 'default'),
        and (x, y, yaw) coordinates.
        """
        try:
            wps = robot.waypoints()
            return {"success": True, "count": len(wps), "waypoints": wps}
        except RobotError as e:
            return {"success": False, "error": f"{e.code}: {e.message}"}

    @mcp.tool()
    def save_current_location_as_waypoint(
        name: str,
        type: str = "default"
    ) -> Dict[str, Any]:
        """Save the robot's current localized position as a named waypoint.
        
        Args:
            name: Unique name for the waypoint (e.g. 'table_1', 'warehouse_exit').
            type: Semantic category: 'dock', 'pickup', 'dropoff', 'patrol', 'default'.
        """
        try:
            # Check localization
            pose = robot.pose()
            if not pose.get("localized", False):
                return {
                    "success": False,
                    "error": "Robot is not localized in the map frame. Cannot save map coordinates."
                }

            res = robot.save_waypoint(name=name, type=type)
            return {
                "success": True,
                "waypoint_name": name,
                "type": type,
                "captured_pose": pose,
                "details": res,
            }
        except RobotError as e:
            return {"success": False, "error": f"{e.code}: {e.message}"}

    @mcp.tool()
    def get_active_map_info() -> Dict[str, Any]:
        """Get dimensions, spatial resolution, and origin metadata of the active navigation map."""
        try:
            info = robot.current_map_info()
            return {
                "success": True,
                "resolution_m_per_pixel": info.get("resolution"),
                "width_pixels": info.get("width"),
                "height_pixels": info.get("height"),
                "origin": info.get("origin"),
                "negate": info.get("negate"),
            }
        except RobotError as e:
            return {"success": False, "error": f"{e.code}: {e.message}"}

    @mcp.tool()
    def list_available_maps() -> Dict[str, Any]:
        """List all saved maps stored on the robot filesystem."""
        try:
            maps = robot.maps()
            current_map = None
            try:
                current_map = robot.current_map()
            except Exception:
                pass
            return {
                "success": True,
                "count": len(maps),
                "active_map": current_map.get("name") if current_map else None,
                "saved_maps": maps,
            }
        except RobotError as e:
            return {"success": False, "error": f"{e.code}: {e.message}"}

    @mcp.tool()
    def switch_active_map(map_name: str) -> Dict[str, Any]:
        """Activate a different map for navigation.
        
        Args:
            map_name: Name of the existing saved map to load into Nav2.
        """
        try:
            res = robot.activate_map(map_name)
            return {"success": True, "active_map": map_name, "details": res}
        except RobotError as e:
            return {"success": False, "error": f"{e.code}: {e.message}"}
