"""Unit tests for navpromini_mcp models, guardrails, tools, and server registration."""

import pytest
from unittest.mock import MagicMock

from navpromini_mcp.models import MissionTask, MissionSpec, ScheduleSpec
from navpromini_mcp.guardrails import (
    validate_waypoints_exist,
    estimate_mission_battery_consumption,
    check_preflight_safety,
    SafetyInterlockError,
)
from navpromini_mcp.server import create_server


def test_mission_models():
    """Verify MissionTask and MissionSpec validation."""
    task1 = MissionTask(waypoint="station_a", action="wait", params={"duration_sec": 10})
    assert task1.waypoint == "station_a"
    assert task1.action == "wait"
    assert task1.params["duration_sec"] == 10

    task2 = MissionTask(waypoint="dock_station", action="dock")
    spec = MissionSpec(name="patrol_test", description="Test run", loop=False, tasks=[task1, task2])
    assert spec.name == "patrol_test"
    assert len(spec.tasks) == 2


def test_guardrails_waypoint_validation():
    """Verify that waypoints validation catches unknown waypoints."""
    tasks = [
        MissionTask(waypoint="known_1"),
        MissionTask(waypoint="unknown_2"),
    ]
    known = {"known_1": {"x": 1.0, "y": 2.0}}
    valid, missing = validate_waypoints_exist(tasks, known)
    assert not valid
    assert missing == ["unknown_2"]


def test_guardrails_battery_estimation():
    """Verify battery consumption calculation based on distance and wait time."""
    tasks = [
        MissionTask(waypoint="wp1", action="wait", params={"duration_sec": 20}),
        MissionTask(waypoint="wp2", action="wait", params={"duration_sec": 10}),
    ]
    known = {
        "wp1": {"x": 0.0, "y": 0.0},
        "wp2": {"x": 3.0, "y": 4.0},  # 5m distance
    }
    est = estimate_mission_battery_consumption(tasks, known, current_pose={"x": 0.0, "y": 0.0})
    assert est["total_distance_m"] == 5.0
    assert est["estimated_duration_sec"] > 30.0
    assert est["estimated_battery_drop_percent"] > 0.0


def test_guardrails_preflight_interlock():
    """Verify low battery triggers SafetyInterlockError on non-dock tasks."""
    mock_robot = MagicMock()
    mock_robot.mode.return_value = {"mode": "navigation"}
    mock_robot.battery.return_value = {"percentage": 7.0}  # Below critical 8%

    # Non-dock destination should raise SafetyInterlockError
    with pytest.raises(SafetyInterlockError) as excinfo:
        check_preflight_safety(mock_robot, is_dock_destination=False)
    assert "CRITICAL SAFETY INTERLOCK" in str(excinfo.value)

    # Dock destination should pass even with low battery
    check_preflight_safety(mock_robot, is_dock_destination=True)


def test_server_creation_and_registration():
    """Verify that the MCP server registers all expected tools, resources, and prompts."""
    server = create_server(robot_host="127.0.0.1", robot_port=8090)

    # Inspect registered tools
    tool_names = list(server._tool_manager._tools.keys())
    assert "synthesize_and_save_mission" in tool_names
    assert "execute_mission" in tool_names
    assert "control_active_mission" in tool_names
    assert "get_mission_status" in tool_names
    assert "list_missions" in tool_names
    assert "schedule_recurring_mission" in tool_names
    assert "list_waypoints" in tool_names
    assert "save_current_location_as_waypoint" in tool_names
    assert "get_active_map_info" in tool_names
    assert "navigate_to_waypoint" in tool_names
    assert "navigate_to_coordinates" in tool_names
    assert "cancel_navigation_goal" in tool_names
    assert "trigger_global_relocalization" in tool_names
    assert "dock_robot" in tool_names
    assert "undock_robot" in tool_names
    assert "cancel_docking" in tool_names
    assert "get_power_status" in tool_names
    assert "emergency_stop" in tool_names
    assert "jog_robot" in tool_names
    assert "get_system_health" in tool_names

    # Inspect registered resources
    resource_uris = list(server._resource_manager._resources.keys())
    assert "robot://telemetry" in resource_uris
    assert "robot://waypoints" in resource_uris
    assert "robot://missions/library" in resource_uris
    assert "robot://missions/active" in resource_uris
    assert "robot://system/health" in resource_uris

    # Inspect registered prompts
    prompt_names = list(server._prompt_manager._prompts.keys())
    assert "facility_patrol_planner" in prompt_names
    assert "robot_fault_recovery" in prompt_names
    assert "preflight_safety_audit" in prompt_names
