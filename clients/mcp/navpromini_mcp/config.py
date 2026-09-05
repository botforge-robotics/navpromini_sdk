"""Configuration settings for NavPro Mini MCP Server."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ServerConfig:
    robot_host: str = os.getenv("NAVPRO_ROBOT_HOST", "192.168.1.50")
    robot_port: int = int(os.getenv("NAVPRO_ROBOT_PORT", "8090"))
    robot_token: Optional[str] = os.getenv("NAVPRO_ROBOT_TOKEN") or None
    
    # Safety thresholds
    min_battery_percent: float = float(os.getenv("NAVPRO_MIN_BATTERY_PERCENT", "15.0"))
    critical_battery_percent: float = float(os.getenv("NAVPRO_CRITICAL_BATTERY_PERCENT", "8.0"))
    
    # Default timeouts
    default_nav_timeout_sec: int = int(os.getenv("NAVPRO_DEFAULT_NAV_TIMEOUT_SEC", "300"))
    default_mission_timeout_sec: int = int(os.getenv("NAVPRO_DEFAULT_MISSION_TIMEOUT_SEC", "1800"))


config = ServerConfig()
