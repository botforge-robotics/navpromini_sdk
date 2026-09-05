"""Mission planning, validation, execution, and scheduling MCP tools."""

from typing import Any, Dict, List, Literal, Optional
from navpromini import NavProMini, RobotError
from navpromini_mcp.guardrails import (
    check_preflight_safety,
    estimate_mission_battery_consumption,
    validate_waypoints_exist,
    SafetyInterlockError,
)
from navpromini_mcp.models import MissionSpec, MissionTask


def register_mission_tools(mcp, robot: NavProMini):
    """Register all mission-related tools on the FastMCP instance."""

    @mcp.tool()
    def synthesize_and_save_mission(
        name: str,
        tasks: List[Dict[str, Any]],
        description: str = "",
        loop: bool = False,
    ) -> Dict[str, Any]:
        """Validate, check battery feasibility, and compile a multi-stop autonomous mission.
        
        Args:
            name: Unique identifier for the mission (alphanumeric and underscores, e.g. 'patrol_warehouse_a').
            tasks: Ordered list of mission tasks. Each task is an object:
                   {"waypoint": "station_1", "action": "wait", "params": {"duration_sec": 10}}.
                   Supported actions: 'wait', 'dock', 'undock', 'inspect', 'call_service'.
            description: Human-readable note detailing the mission objective.
            loop: Set to True if the mission should continuously cycle through tasks indefinitely.
        
        Returns:
            Validation and compile summary, including estimated distance, battery consumption, and save status.
        """
        # Parse into typed tasks
        parsed_tasks: List[MissionTask] = []
        for i, t in enumerate(tasks):
            if "waypoint" not in t:
                return {
                    "success": False,
                    "error": f"Task #{i} is missing required 'waypoint' field."
                }
            parsed_tasks.append(
                MissionTask(
                    waypoint=t["waypoint"],
                    action=t.get("action", "wait"),
                    params=t.get("params", {}),
                )
            )

        # 1. Fetch map waypoints to validate existence
        try:
            raw_wps = robot.waypoints()
            known_wps = {w["name"]: w for w in raw_wps}
        except Exception as e:
            return {"success": False, "error": f"Could not retrieve robot waypoints: {str(e)}"}

        valid, missing = validate_waypoints_exist(parsed_tasks, known_wps)
        if not valid:
            return {
                "success": False,
                "error": f"Waypoints not found in current map: {missing}. Available waypoints: {list(known_wps.keys())}"
            }

        # 2. Estimate battery consumption
        try:
            curr_pose = robot.pose()
            batt = robot.battery()
            curr_batt_percent = batt.get("percentage", 100.0)
        except Exception:
            curr_pose = None
            curr_batt_percent = 100.0

        feasibility = estimate_mission_battery_consumption(parsed_tasks, known_wps, curr_pose)
        needed_batt = feasibility["estimated_battery_drop_percent"]

        # If loop is False, check if the mission can finish
        if not loop and (curr_batt_percent - needed_batt) < 15.0:
            warning = (
                f"BATTERY BUDGET WARNING: Mission requires estimated {needed_batt:.1f}% battery. "
                f"Current battery is {curr_batt_percent:.1f}%. "
                f"Predicted remaining after mission: {curr_batt_percent - needed_batt:.1f}% (below 15% safety buffer)."
            )
        else:
            warning = None

        # 3. Save mission definition to robot
        mission_payload = {
            "name": name,
            "description": description,
            "loop": loop,
            "tasks": [t.model_dump() for t in parsed_tasks],
        }

        try:
            save_result = robot.save_mission(mission_payload)
            return {
                "success": True,
                "mission_name": name,
                "task_count": len(parsed_tasks),
                "feasibility": feasibility,
                "warning": warning,
                "details": save_result,
            }
        except RobotError as e:
            return {"success": False, "error": f"Failed to save mission on robot: {e.code} - {e.message}"}

    @mcp.tool()
    def execute_mission(
        mission_name: str,
        wait_for_completion: bool = False,
        timeout_sec: int = 1800
    ) -> Dict[str, Any]:
        """Start executing a saved mission by name.
        
        Args:
            mission_name: The name of the previously saved mission.
            wait_for_completion: If True, blocks and monitors the mission until completed, failed, or timed out.
            timeout_sec: Maximum seconds to wait if wait_for_completion is True (default: 1800s / 30m).
        
        Returns:
            Execution status, current task index, and completion result if waited.
        """
        # Pre-flight safety checks
        try:
            check_preflight_safety(robot)
        except SafetyInterlockError as err:
            return {"success": False, "error": str(err)}

        try:
            robot.start_mission(mission_name)
        except RobotError as e:
            return {"success": False, "error": f"Failed to start mission: {e.code} - {e.message}"}

        if not wait_for_completion:
            return {
                "success": True,
                "state": "started",
                "mission": mission_name,
                "message": "Mission started asynchronously. Use 'get_mission_status' to monitor progress."
            }

        try:
            final_status = robot.wait_for_mission(timeout_s=timeout_sec)
            return {
                "success": True,
                "state": final_status.get("state", "completed"),
                "mission": mission_name,
                "details": final_status,
            }
        except TimeoutError:
            return {
                "success": False,
                "state": "timed_out",
                "error": f"Mission timed out after {timeout_sec}s. Robot is still running or paused."
            }
        except Exception as e:
            return {"success": False, "error": f"Error waiting for mission: {str(e)}"}

    @mcp.tool()
    def control_active_mission(
        action: Literal["pause", "resume", "cancel"]
    ) -> Dict[str, Any]:
        """Pause, resume, or cancel the currently executing mission.
        
        Args:
            action: 
              - 'pause': Freezes the active mission and halts robot movement in place.
              - 'resume': Continues mission execution from the paused step.
              - 'cancel': Aborts the mission and stops all navigation goals.
        """
        try:
            if action == "pause":
                res = robot.pause_mission()
                return {"success": True, "action": "pause", "message": "Mission paused successfully.", "details": res}
            elif action == "resume":
                check_preflight_safety(robot)
                res = robot.resume_mission()
                return {"success": True, "action": "resume", "message": "Mission resumed successfully.", "details": res}
            elif action == "cancel":
                res = robot.cancel_mission()
                return {"success": True, "action": "cancel", "message": "Active mission cancelled.", "details": res}
        except SafetyInterlockError as err:
            return {"success": False, "error": str(err)}
        except RobotError as e:
            return {"success": False, "error": f"Mission control error: {e.code} - {e.message}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def get_mission_status() -> Dict[str, Any]:
        """Get live execution state of the currently active or most recent mission."""
        try:
            status = robot.mission_status()
            return {"success": True, "data": status}
        except RobotError as e:
            return {"success": False, "error": f"{e.code}: {e.message}"}

    @mcp.tool()
    def list_missions() -> Dict[str, Any]:
        """List all saved missions stored in the robot's memory."""
        try:
            missions_list = robot.missions()
            return {"success": True, "count": len(missions_list), "missions": missions_list}
        except RobotError as e:
            return {"success": False, "error": f"{e.code}: {e.message}"}

    @mcp.tool()
    def schedule_recurring_mission(
        schedule_id: str,
        mission_name: str,
        cron: str,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """Schedule a mission to run periodically at automated intervals using cron syntax.
        
        Args:
            schedule_id: Unique identifier for the schedule (e.g. 'hourly_aisle_scan').
            mission_name: Name of the existing mission to execute.
            cron: Standard 5-field cron expression: 'minute hour day-of-month month day-of-week'
                  Examples:
                    '0 8 * * *'    -> Every day at 8:00 AM
                    '*/30 * * * *' -> Every 30 minutes
                    '0 9,17 * * 1-5' -> At 9 AM and 5 PM on weekdays
            enabled: Whether the schedule should be active immediately.
        """
        # Check mission exists
        try:
            saved = robot.missions()
            names = [m.get("name") for m in saved]
            if mission_name not in names:
                return {
                    "success": False,
                    "error": f"Mission '{mission_name}' does not exist. Available missions: {names}"
                }
        except Exception as e:
            return {"success": False, "error": f"Failed checking missions: {str(e)}"}

        schedule_payload = {
            "id": schedule_id,
            "mission_name": mission_name,
            "cron": cron,
            "enabled": enabled,
        }

        try:
            res = robot.save_schedule(schedule_payload)
            return {
                "success": True,
                "schedule_id": schedule_id,
                "mission_name": mission_name,
                "cron": cron,
                "enabled": enabled,
                "details": res,
            }
        except RobotError as e:
            return {"success": False, "error": f"Failed to save schedule: {e.code} - {e.message}"}

    @mcp.tool()
    def list_schedules() -> Dict[str, Any]:
        """List all configured automated cron schedules on the robot."""
        try:
            schedules = robot.schedules()
            return {"success": True, "count": len(schedules), "schedules": schedules}
        except RobotError as e:
            return {"success": False, "error": f"{e.code}: {e.message}"}
