#!/usr/bin/env python3
"""Arrow-key teleop in a terminal.

    python3 teleop.py

Arrows drive, space stops, q quits. Velocity commands expire after ~0.5s, so
this resends at 5Hz — release the keys and the robot stops on its own.
"""

import curses
import os
import time

from navpromini import NavProMini

LINEAR = 0.15        # m/s
ANGULAR = 0.6        # rad/s
RATE = 5.0           # Hz


def run(screen, robot: NavProMini) -> None:
    curses.curs_set(0)
    screen.nodelay(True)
    screen.addstr(0, 0, f'NavProMini teleop — {robot.host}')
    screen.addstr(1, 0, 'arrows: drive   space: stop   q: quit')

    linear = angular = 0.0
    last_key = time.time()

    while True:
        key = screen.getch()
        if key != -1:
            last_key = time.time()
            if key in (ord('q'), 27):
                break
            if key == curses.KEY_UP:
                linear, angular = LINEAR, 0.0
            elif key == curses.KEY_DOWN:
                linear, angular = -LINEAR, 0.0
            elif key == curses.KEY_LEFT:
                linear, angular = 0.0, ANGULAR
            elif key == curses.KEY_RIGHT:
                linear, angular = 0.0, -ANGULAR
            elif key == ord(' '):
                linear = angular = 0.0

        # No key for a moment means the operator let go. Coast to a stop
        # rather than continuing on the last command.
        if time.time() - last_key > 0.4:
            linear = angular = 0.0

        robot.velocity_command(linear=linear, angular=angular)

        battery = ''
        try:
            battery = f"{robot.battery()['percentage']:.0f}%"
        except Exception:
            pass

        screen.addstr(3, 0, f'linear {linear:+.2f} m/s   '
                            f'angular {angular:+.2f} rad/s   battery {battery}   ')
        screen.refresh()
        time.sleep(1.0 / RATE)

    robot.stop()


if __name__ == '__main__':
    bot = NavProMini(os.environ.get('ROBOT_HOST', 'navpromini.local'),
                     token=os.environ.get('ROBOT_TOKEN') or None)
    try:
        curses.wrapper(run, bot)
    finally:
        bot.stop()
        print('stopped')
