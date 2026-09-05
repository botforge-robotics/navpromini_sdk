"""NavPro Mini Autonomous Robotics Model Context Protocol (MCP) Server."""

import argparse
import sys
from typing import Optional

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

from navpromini import NavProMini
from navpromini_mcp.config import config
from navpromini_mcp.prompts import register_prompts
from navpromini_mcp.resources import register_resources
from navpromini_mcp.tools.emergency import register_emergency_tools
from navpromini_mcp.tools.missions import register_mission_tools
from navpromini_mcp.tools.navigation import register_navigation_tools
from navpromini_mcp.tools.power import register_power_tools
from navpromini_mcp.tools.spatial import register_spatial_tools


def create_server(
    robot_host: Optional[str] = None,
    robot_port: Optional[int] = None,
    robot_token: Optional[str] = None,
) -> MCPServer:
    """Create and configure the NavPro Mini MCP Server instance."""
    host = robot_host or config.robot_host
    port = robot_port or config.robot_port
    token = robot_token or config.robot_token

    # 1. Initialize Robot SDK client
    robot = NavProMini(host=host, port=port, token=token)

    # 2. Initialize MCP server instance
    server = MCPServer(name="NavProMini-Robotics")

    # 3. Register tool categories
    register_mission_tools(server, robot)
    register_spatial_tools(server, robot)
    register_navigation_tools(server, robot)
    register_power_tools(server, robot)
    register_emergency_tools(server, robot)

    # 4. Register passive read resources
    register_resources(server, robot)

    # 5. Register reusable agent prompts
    register_prompts(server)

    return server


def main():
    """Main CLI entrypoint for running the MCP server."""
    parser = argparse.ArgumentParser(description="NavPro Mini Robotics MCP Server")
    parser.add_argument("--host", default=None, help="Robot IP or hostname (default: NAVPRO_ROBOT_HOST or 192.168.1.50)")
    parser.add_argument("--port", type=int, default=None, help="Robot API port (default: NAVPRO_ROBOT_PORT or 8090)")
    parser.add_argument("--token", default=None, help="Optional Bearer token for robot authentication")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP transport protocol: 'stdio' for CLI/desktop agents, 'sse' for HTTP network agents (default: stdio)",
    )
    parser.add_argument("--sse-port", type=int, default=8091, help="Port for SSE transport server (default: 8091)")

    args = parser.parse_args()

    server = create_server(
        robot_host=args.host,
        robot_port=args.port,
        robot_token=args.token,
    )

    if args.transport == "stdio":
        server.run(transport="stdio")
    elif args.transport == "sse":
        server.run(transport="sse", port=args.sse_port)


if __name__ == "__main__":
    main()
