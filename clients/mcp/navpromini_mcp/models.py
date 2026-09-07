"""Pydantic data models and schemas for MCP tool parameters and responses."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class Pose2D(BaseModel):
    x: float = Field(..., description="X coordinate in meters in the map frame")
    y: float = Field(..., description="Y coordinate in meters in the map frame")
    yaw: float = Field(0.0, description="Orientation angle in radians (-pi to +pi)")


class MissionTask(BaseModel):
    waypoint: Optional[str] = Field(
        default=None,
        description="Target waypoint name defined in the active map (optional for actions like dock, undock, call_api)"
    )
    action: Literal["wait", "dock", "undock", "inspect", "call_service", "call_action", "call_api", "custom"] = Field(
        default="wait",
        description="Action to execute upon arrival at the waypoint"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional action parameters, e.g. {'duration_sec': 10} or for call_api: {'url': '...', 'method': 'POST', 'payload': {...}, 'headers': {...}, 'timeout_sec': 10}"
    )
    url: Optional[str] = Field(default=None, description="Target HTTP/HTTPS URL when action is 'call_api'")
    method: Optional[str] = Field(default=None, description="HTTP method for 'call_api' (e.g. GET, POST, PUT, DELETE, PATCH)")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Optional HTTP request headers for 'call_api'")
    payload: Optional[Any] = Field(default=None, description="Optional request payload/body for 'call_api'")
    timeout_sec: Optional[float] = Field(default=None, description="Timeout in seconds for 'call_api', 'call_service', or 'call_action'")
    ignore_error: Optional[bool] = Field(default=None, description="If true, HTTP errors will not fail the mission")
    service: Optional[str] = Field(default=None, description="ROS 2 service name when action is 'call_service' (e.g. '/camera/capture', '/clear_costmaps')")
    service_type: Optional[str] = Field(default=None, description="ROS 2 service type when action is 'call_service' (e.g. 'std_srvs/srv/Trigger')")
    request: Optional[Dict[str, Any]] = Field(default=None, description="Optional service request dictionary for 'call_service'")
    action_name: Optional[str] = Field(default=None, description="ROS 2 action name when action is 'call_action' (e.g. '/spin', '/backup')")
    action_type: Optional[str] = Field(default=None, description="ROS 2 action type when action is 'call_action' (e.g. 'nav2_msgs/action/Spin')")
    goal: Optional[Dict[str, Any]] = Field(default=None, description="Optional action goal dictionary for 'call_action'")


class MissionSpec(BaseModel):
    name: str = Field(..., description="Unique alphanumeric mission identifier (no spaces)")
    description: str = Field("", description="Human-readable description of the mission purpose")
    loop: bool = Field(False, description="Whether to repeat the task sequence in an infinite loop")
    tasks: List[MissionTask] = Field(..., min_length=1, description="Ordered sequence of waypoint tasks")


class ScheduleSpec(BaseModel):
    id: str = Field(..., description="Unique schedule identifier (e.g. 'morning_inspection_0800')")
    mission_name: str = Field(..., description="Name of the saved mission to execute")
    cron: str = Field(..., description="Standard 5-field cron expression, e.g. '0 8 * * *'")
    enabled: bool = Field(True, description="Whether the recurring schedule is currently active")


class RobotStatusSummary(BaseModel):
    robot_name: str
    mode: str
    battery_percentage: float
    battery_voltage: float
    is_charging: bool
    battery_status: str
    localized: bool
    pose: Optional[Dict[str, Any]] = None
    linear_velocity: float = 0.0
    angular_velocity: float = 0.0
    active_mission_state: Optional[str] = None
