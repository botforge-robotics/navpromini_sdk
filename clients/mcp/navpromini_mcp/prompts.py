"""MCP prompt templates for standard autonomous robotics agent workflows."""

from typing import Any


def register_prompts(mcp: Any):
    """Register reusable agent runbook prompts on the FastMCP instance."""

    @mcp.prompt()
    def facility_patrol_planner() -> str:
        """Runbook to design, validate, and deploy an autonomous patrol mission."""
        return (
            "You are the autonomous fleet coordinator for the NavPro Mini AMR.\n\n"
            "Follow these steps to plan and schedule a facility patrol:\n"
            "1. First, call 'list_waypoints' to see all known landmarks in the active map.\n"
            "2. Call 'get_power_status' to ensure the robot has sufficient battery (>50% recommended).\n"
            "3. Ask the user or determine the patrol sequence (e.g. Aisle 1 -> Aisle 2 -> Charging Dock).\n"
            "4. Call 'synthesize_and_save_mission' with the list of tasks. Ensure each task has a valid waypoint "
            "and action (e.g. 'wait' for 10s at inspection points, and 'dock' at the final dock station).\n"
            "5. Review the returned battery feasibility estimate. If predicted remaining battery is low, advise adding a dock stop.\n"
            "6. If the user requested periodic execution, call 'schedule_recurring_mission' with an appropriate cron expression.\n"
            "7. Finally, report the mission name, task count, and estimated duration to the operator."
        )

    @mcp.prompt()
    def robot_fault_recovery() -> str:
        """Step-by-step triage guide when the robot encounters navigation failure, obstacles, or lost localization."""
        return (
            "You are diagnosing a NavPro Mini AMR that reported a navigation error or fault.\n\n"
            "Execute the following triage procedure:\n"
            "1. Call 'get_system_health' to check sensor topic freshness (LiDAR, scan, odometry) and node lifecycles.\n"
            "2. Call 'get_power_status' to verify battery voltage and state.\n"
            "3. Check 'get_navigation_status' to identify the failure code (e.g. 'obstacle_blocked', 'goal_rejected').\n"
            "4. If localization is lost or unconfirmed:\n"
            "   - Call 'trigger_global_relocalization' to disperse AMCL particles and perform an environment sweep.\n"
            "   - Verify if localized flag turns True.\n"
            "5. If physically obstructed or trapped in a local minimum:\n"
            "   - Call 'jog_robot(distance_m=-0.2)' to cautiously reverse 20 cm away from obstacles.\n"
            "   - Re-attempt navigation to the target waypoint or fallback to 'dock_robot'.\n"
            "6. In all ambiguous or unsafe situations, execute 'emergency_stop' and alert the human supervisor."
        )

    @mcp.prompt()
    def preflight_safety_audit() -> str:
        """Inspect robot hardware, battery, and localization before starting a production shift."""
        return (
            "Perform a complete pre-flight check of the NavPro Mini AMR:\n\n"
            "1. Query 'get_power_status'. Verify battery >= 20%.\n"
            "2. Query 'get_system_health'. Confirm all sensors and lifecycle nodes report 'healthy' or 'active'.\n"
            "3. Inspect 'list_waypoints'. Confirm the target destinations and 'dock' station are configured.\n"
            "4. Confirm the robot is localized in the map frame.\n"
            "5. Output a structured Go/No-Go readiness verdict to the operator."
        )
