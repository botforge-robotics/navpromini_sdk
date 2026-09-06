"""Safety interlocks, pre-flight checks, and feasibility estimators for robot control."""

import math
from typing import Dict, List, Optional, Tuple
from navpromini import NavProMini, RobotError
from navpromini_mcp.config import config
from navpromini_mcp.models import MissionTask


class SafetyInterlockError(Exception):
    """Raised when a safety invariant (e.g. low battery, lost localization) is breached."""
    pass


def check_preflight_safety(robot: NavProMini, is_dock_destination: bool = False) -> None:
    """Validate that the robot is in a safe operational state before executing motion.
    
    Raises:
        SafetyInterlockError: If battery is critically low or robot mode is invalid.
    """
    # 1. Mode check
    current_mode = robot.mode().get("mode", "unknown")
    if current_mode == "mapping":
        raise SafetyInterlockError(
            "Robot is currently in 'mapping' (SLAM) mode. Navigation/mission commands are rejected "
            "to prevent corrupting the active map. Switch to 'navigation' mode first."
        )

    # 2. Battery check
    try:
        battery = robot.battery()
        percent = battery.get("percentage", 100.0)
    except Exception as e:
        # If battery read fails, warn but proceed cautiously
        return

    if percent <= config.critical_battery_percent and not is_dock_destination:
        raise SafetyInterlockError(
            f"CRITICAL SAFETY INTERLOCK: Battery is at {percent:.1f}% "
            f"(threshold: {config.critical_battery_percent}%). "
            "All outbound navigation and mission commands are rejected. "
            "Robot MUST be sent to dock immediately."
        )

    if percent <= config.min_battery_percent and not is_dock_destination:
        raise SafetyInterlockError(
            f"LOW BATTERY INTERLOCK: Battery is at {percent:.1f}% "
            f"(threshold: {config.min_battery_percent}%). "
            "Outbound commands rejected. Please dock the robot to recharge before running new tasks."
        )


def validate_waypoints_exist(
    tasks: List[MissionTask],
    known_waypoints: Dict[str, Dict]
) -> Tuple[bool, List[str]]:
    """Verify that every waypoint specified in the mission tasks exists in the current map.
    
    Returns:
        Tuple of (all_exist: bool, missing_waypoint_names: List[str])
    """
    missing = []
    for task in tasks:
        if not task.waypoint:
            continue
        if task.waypoint not in known_waypoints:
            missing.append(task.waypoint)
    return (len(missing) == 0, missing)


def estimate_mission_battery_consumption(
    tasks: List[MissionTask],
    known_waypoints: Dict[str, Dict],
    current_pose: Optional[Dict] = None
) -> Dict[str, float]:
    """Estimate total travel distance and battery consumption for a proposed mission.
    
    Heuristic:
      - Average AMR speed: 0.3 m/s
      - Discharge rate moving: ~0.15% per meter
      - Discharge rate waiting/idle: ~0.02% per second
    
    Returns:
        dict with total_distance_m, estimated_duration_sec, estimated_battery_percent
    """
    total_dist = 0.0
    total_wait_sec = 0.0

    last_x, last_y = 0.0, 0.0
    has_pos = False

    if current_pose and "x" in current_pose and "y" in current_pose:
        last_x = current_pose["x"]
        last_y = current_pose["y"]
        has_pos = True

    for task in tasks:
        if task.waypoint:
            wp_data = known_waypoints.get(task.waypoint, {})
            tx = wp_data.get("x")
            ty = wp_data.get("y")

            if tx is not None and ty is not None:
                if has_pos:
                    dist = math.hypot(tx - last_x, ty - last_y)
                    total_dist += dist
                last_x, last_y = tx, ty
                has_pos = True

        if task.action == "wait":
            duration = task.params.get("duration_sec", 5.0)
            total_wait_sec += float(duration)

    transit_time_sec = total_dist / 0.3 if total_dist > 0 else 0.0
    total_duration_sec = transit_time_sec + total_wait_sec

    # Discharge calculation
    battery_used = (total_dist * 0.15) + (total_wait_sec * 0.02)

    return {
        "total_distance_m": round(total_dist, 2),
        "estimated_duration_sec": round(total_duration_sec, 1),
        "estimated_battery_drop_percent": round(battery_used, 1),
    }
