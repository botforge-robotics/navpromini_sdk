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


def test_call_api_model_and_compilation():
    """Verify call_api action in MissionTask and synthesize_and_save_mission tool."""
    # 1. Model test with params
    task = MissionTask(
        waypoint="inspection_bay",
        action="call_api",
        params={
            "url": "http://192.168.0.175:8080/capture-and-report",
            "method": "POST",
            "payload": {"test": True},
            "timeout_sec": 10.0,
            "ignore_error": True,
        }
    )
    assert task.action == "call_api"
    assert task.waypoint == "inspection_bay"

    # 2. Tool compilation test
    mock_robot = MagicMock()
    mock_robot.waypoints.return_value = [{"name": "inspection_bay", "x": 1.0, "y": 2.0}]
    mock_robot.pose.return_value = {"x": 0.0, "y": 0.0}
    mock_robot.battery.return_value = {"percentage": 90.0}
    mock_robot.save_mission.return_value = {"id": "test_api_mission", "saved": True}

    from navpromini_mcp.tools.missions import register_mission_tools
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError:
        from mcp.server.fastmcp import FastMCP as MCPServer

    test_mcp = MCPServer(name="test_mcp")
    register_mission_tools(test_mcp, mock_robot)

    synth_tool = test_mcp._tool_manager._tools["synthesize_and_save_mission"].fn
    res = synth_tool(
        name="test_api_mission",
        tasks=[
            {
                "waypoint": "inspection_bay",
                "action": "call_api",
                "params": {
                    "url": "http://192.168.0.175:8080/capture-and-report",
                    "method": "POST",
                    "payload": {"status": "arrived"},
                }
            },
            {
                "action": "call_api",
                "url": "http://192.168.0.175:8080/done",
                "method": "GET",
            }
        ]
    )

    assert res["success"] is True
    steps = res["steps"]
    assert len(steps) == 3
    # Step 1: navigate to inspection_bay
    assert steps[0] == {"type": "navigate", "target": "inspection_bay"}
    # Step 2: call_api POST
    assert steps[1]["type"] == "call_api"
    assert steps[1]["url"] == "http://192.168.0.175:8080/capture-and-report"
    assert steps[1]["method"] == "POST"
    assert steps[1]["payload"] == {"status": "arrived"}
    # Step 3: call_api GET (no waypoint, so no preceding navigate step)
    assert steps[2]["type"] == "call_api"
    assert steps[2]["url"] == "http://192.168.0.175:8080/done"
    assert steps[2]["method"] == "GET"


def test_call_service_and_action_compilation():
    """Verify call_service and call_action task compilation."""
    mock_robot = MagicMock()
    mock_robot.waypoints.return_value = [{"name": "inspection_bay", "x": 1.0, "y": 2.0}]
    mock_robot.pose.return_value = {"x": 0.0, "y": 0.0}
    mock_robot.battery.return_value = {"percentage": 90.0}
    mock_robot.save_mission.return_value = {"id": "ros_mission", "saved": True}

    from navpromini_mcp.tools.missions import register_mission_tools
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError:
        from mcp.server.fastmcp import FastMCP as MCPServer

    test_mcp = MCPServer(name="test_mcp_ros")
    register_mission_tools(test_mcp, mock_robot)

    synth_tool = test_mcp._tool_manager._tools["synthesize_and_save_mission"].fn
    res = synth_tool(
        name="ros_mission",
        tasks=[
            {
                "waypoint": "inspection_bay",
                "action": "call_service",
                "service": "/camera/capture",
                "service_type": "std_srvs/srv/Trigger",
                "request": {},
                "timeout_sec": 8.0,
            },
            {
                "action": "call_action",
                "action_name": "/spin",
                "action_type": "nav2_msgs/action/Spin",
                "goal": {"target_yaw": 3.14},
                "timeout_sec": 25.0,
            }
        ]
    )

    assert res["success"] is True
    steps = res["steps"]
    assert len(steps) == 3
    # Step 0: navigate
    assert steps[0] == {"type": "navigate", "target": "inspection_bay"}
    # Step 1: call_service
    assert steps[1]["type"] == "call_service"
    assert steps[1]["service"] == "/camera/capture"
    assert steps[1]["service_type"] == "std_srvs/srv/Trigger"
    assert steps[1]["request"] == {}
    assert steps[1]["timeout"] == 8.0
    # Step 2: call_action
    assert steps[2]["type"] == "call_action"
    assert steps[2]["action"] == "/spin"
    assert steps[2]["action_type"] == "nav2_msgs/action/Spin"
    assert steps[2]["goal"] == {"target_yaw": 3.14}
    assert steps[2]["timeout"] == 25.0

