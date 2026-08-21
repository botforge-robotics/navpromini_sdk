"""Python client for the NavProMini SDK API.

    from navpromini import NavProMini

    robot = NavProMini("192.168.1.50")
    print(robot.battery()["percentage"])
    robot.goto(waypoint="kitchen", wait=True)
    robot.dock(wait=True)
"""

from .client import ApiError, NavProMini, RobotError

__all__ = ['NavProMini', 'RobotError', 'ApiError']
__version__ = '1.0.0'
