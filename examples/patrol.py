#!/usr/bin/env python3
"""Drive a waypoint loop, docking to charge when the battery gets low.

    python3 patrol.py workRoom kitchen hallway entrance

First argument is the map; the rest are waypoints, visited in order, forever.
"""

import os
import sys
import time

from navpromini import NavProMini, RobotError

DOCK_BELOW = 20      # percent — go charge
RESUME_AT = 80       # percent — resume patrolling
DWELL = 5            # seconds at each stop


def ensure_charged(robot: NavProMini) -> bool:
    """Dock and wait if low. True if it charged."""
    level = robot.battery()['percentage']
    if level >= DOCK_BELOW:
        return False

    print(f'battery {level:.0f}% — docking')
    robot.cancel_goal()
    robot.dock(wait=True, timeout=420)
    print('charging')

    while True:
        level = robot.battery()['percentage']
        print(f'  {level:.0f}%')
        if level >= RESUME_AT:
            break
        time.sleep(60)

    print('resuming patrol')     # goto() undocks by itself
    return True


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(f'usage: {sys.argv[0]} <map> <waypoint> [waypoint …]')

    map_name, route = sys.argv[1], sys.argv[2:]
    robot = NavProMini(os.environ.get('ROBOT_HOST', '192.168.1.50'),
                       token=os.environ.get('ROBOT_TOKEN') or None)

    if robot.mode()['mode'] != 'navigation' or robot.current_map() != map_name:
        print(f'starting navigation on {map_name}')
        robot.start_navigation(map_name, wait=True, timeout=90)

    pose = robot.pose()
    if not pose['localized']:
        sys.exit('robot is not localized — send /navigation/localize first, '
                 'or use the app to set a pose estimate')

    known = {w['name'] for w in robot.waypoints(map_name)}
    missing = [w for w in route if w not in known]
    if missing:
        sys.exit(f'unknown waypoint(s): {", ".join(missing)}\n'
                 f'known: {", ".join(sorted(known))}')

    print(f'patrolling: {" -> ".join(route)}\n')
    lap = 0
    while True:
        lap += 1
        for stop in route:
            if ensure_charged(robot):
                continue
            try:
                print(f'[lap {lap}] -> {stop}')
                robot.goto(waypoint=stop, wait=True, timeout=240)
                print(f'[lap {lap}]    reached {stop}')
                time.sleep(DWELL)
            except TimeoutError:
                print(f'[lap {lap}]    {stop} took too long — cancelling')
                robot.cancel_goal()
            except RobotError as exc:
                print(f'[lap {lap}]    {stop} failed: {exc.code} — {exc.message}')
                time.sleep(5)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nstopping')
