"""Python client for the NavProMini SDK API.

    from navpromini import NavProMini

    robot = NavProMini("navpromini.local")
    print(robot.battery()["percentage"])
    robot.goto(waypoint="kitchen", wait=True)
    robot.dock(wait=True)
"""

from .client import ApiError, NavProMini, RobotError

__all__ = ['NavProMini', 'RobotError', 'ApiError']
__version__ = '1.0.0'
