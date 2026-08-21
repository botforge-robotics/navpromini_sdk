#!/usr/bin/env python3
"""Print frames from the robot's event stream.

    python3 watch_events.py                    # pose + battery
    python3 watch_events.py pose scan dock_status
"""

import os
import sys
import time

from navpromini import NavProMini

STREAMS = sys.argv[1:] or ['pose', 'battery', 'dock_status']


def main() -> None:
    robot = NavProMini(os.environ.get('ROBOT_HOST', '192.168.1.50'),
                       token=os.environ.get('ROBOT_TOKEN') or None)
    print(f'connecting to {robot.host} — streams: {", ".join(STREAMS)}')
    print('ctrl-c to stop\n')

    counts: dict[str, int] = {}
    started = time.time()

    for frame in robot.events(STREAMS):
        stream = frame['stream']
        counts[stream] = counts.get(stream, 0) + 1

        if stream == 'hello':
            print(f'available: {", ".join(frame["data"]["streams"])}\n')
            continue
        if stream == 'error':
            print(f'! {frame["data"]["code"]}: {frame["data"]["message"]}')
            continue
        if stream == 'subscribed':
            print(f'subscribed: {", ".join(frame["data"]["streams"])}\n')
            continue

        data = frame.get('data')
        if stream in ('pose', 'pose_odom'):
            summary = (f'x={data["x"]:7.3f}  y={data["y"]:7.3f}  '
                       f'theta={data["theta"]:6.3f}  [{data["frame"]}]')
        elif stream == 'battery':
            summary = (f'{data["percentage"]:5.1f}%  {data["voltage"]:.2f}V  '
                       f'{data["current"]:+.2f}A  {data["status"]}')
        elif stream == 'scan':
            hits = [r for r in data['ranges'] if r is not None]
            summary = f'{len(hits)}/{data["count"]} returns, nearest {min(hits):.2f}m'
        elif stream == 'velocity':
            summary = f'linear={data["linear"]:+.3f}  angular={data["angular"]:+.3f}'
        else:
            summary = str(data)

        print(f'{time.time() - started:7.1f}s  {stream:<16} {summary}')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nstopped')
