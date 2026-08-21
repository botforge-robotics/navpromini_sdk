"""A thin, synchronous client for the NavProMini SDK.

Thin on purpose. Every method maps to one endpoint, keeps the server's field
names, and adds nothing the API did not say. The only real conveniences are
`wait=True` helpers around the endpoints that return 202, because polling for a
terminal state is the one piece of boilerplate every caller would otherwise
write — and get subtly wrong.

Requires `requests`. `websocket-client` is needed only for `events()`.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Iterator, Optional

import requests

DEFAULT_PORT = 8090
API_PREFIX = '/api/v1'

# Terminal states, so callers and the wait helpers agree on what "done" means.
NAV_DONE = ('succeeded', 'failed', 'canceled')
DOCK_DONE = ('docked', 'undocked', 'failed', 'idle')


class RobotError(Exception):
    """A typed error from the robot.

    Carries the server's `code` so callers can branch on it. The message is for
    humans and may change between versions; the code will not.
    """

    def __init__(self, code: str, message: str, detail: dict, status: int) -> None:
        super().__init__(f'{code}: {message}')
        self.code = code
        self.message = message
        self.detail = detail or {}
        self.status = status

    def __repr__(self) -> str:
        return f'RobotError({self.code!r}, status={self.status})'


# Older name, kept so existing imports keep working.
ApiError = RobotError


class NavProMini:
    """Talks to one robot.

    Args:
        host: robot IP address, e.g. `192.168.1.50`. A hostname works too,
            but an IP resolves from anywhere that can route to the robot.
        port: defaults to 8090.
        token: bearer token, if the robot has auth enabled.
        timeout: per-request timeout in seconds. Note this bounds the HTTP
            call, not the robot's operation — long operations return 202
            immediately, so a short timeout here is correct.
    """

    def __init__(self, host: str, port: int = DEFAULT_PORT,
                 token: Optional[str] = None, timeout: float = 10.0) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.timeout = timeout
        self.base = f'http://{host}:{port}{API_PREFIX}'
        self._session = requests.Session()
        if token:
            self._session.headers['Authorization'] = f'Bearer {token}'

    # -- plumbing ----------------------------------------------------------

    def _request(self, method: str, path: str, **kw: Any) -> Any:
        kw.setdefault('timeout', self.timeout)
        response = self._session.request(method, f'{self.base}{path}', **kw)
        if response.ok:
            return response.json() if response.content else {}
        try:
            err = response.json().get('error', {})
        except ValueError:
            # Not our error shape at all — a proxy, or the wrong port entirely.
            raise RobotError('http_error', response.text[:200] or response.reason,
                             {}, response.status_code)
        raise RobotError(err.get('code', 'unknown'),
                         err.get('message', response.reason),
                         err.get('detail', {}), response.status_code)

    def _get(self, path: str, **params: Any) -> Any:
        clean = {k: v for k, v in params.items() if v is not None}
        return self._request('GET', path, params=clean or None)

    def _post(self, path: str, body: Optional[dict] = None) -> Any:
        return self._request('POST', path, json=body or {})

    def _put(self, path: str, body: dict) -> Any:
        return self._request('PUT', path, json=body)

    def _delete(self, path: str, **params: Any) -> Any:
        clean = {k: v for k, v in params.items() if v is not None}
        return self._request('DELETE', path, params=clean or None)

    # -- system ------------------------------------------------------------

    def info(self) -> dict:
        """Identity, versions and capabilities."""
        return self._get('/system/info')

    def health(self) -> dict:
        """Per-subsystem freshness."""
        return self._get('/system/health')

    def is_healthy(self) -> bool:
        return bool(self.health().get('healthy'))

    def capabilities(self) -> dict:
        return self.info().get('capabilities', {})

    # -- state -------------------------------------------------------------
    #
    # These unwrap `data` and drop `age_sec`, because the common case is
    # "give me the reading". Anything that needs the age uses state_raw().

    def state_raw(self, what: str) -> dict:
        """The full envelope for a state endpoint, including `age_sec`."""
        return self._get(f'/state/{what}')

    def pose(self) -> dict:
        """Current pose, with `localized` folded in.

        `localized` is merged into the returned dict rather than dropped: a
        pose without it is easy to misuse, and `frame` alone is a subtler
        signal than most callers will notice.
        """
        payload = self._get('/state/pose')
        data = dict(payload['data'])
        data['localized'] = payload.get('localized', False)
        data['age_sec'] = payload.get('age_sec')
        return data

    def velocity(self) -> dict:
        return self._get('/state/velocity')['data']

    def battery(self) -> dict:
        return self._get('/state/battery')['data']

    def imu(self) -> dict:
        return self._get('/state/imu')['data']

    def scan(self) -> dict:
        return self._get('/state/scan')['data']

    def temperature(self) -> dict:
        return self._get('/state/temperature')

    def is_charging(self) -> bool:
        """Ground truth for being on the dock — current is actually flowing."""
        return bool(self.battery().get('charging'))

    # -- mode --------------------------------------------------------------

    def mode(self) -> dict:
        return self._get('/mode')

    def set_mode(self, mode: str, map_name: Optional[str] = None,
                 wait: bool = False, timeout: float = 60.0) -> dict:
        """Switch mode. With wait=True, block until it has settled.

        Waiting polls GET /mode rather than trusting a fixed sleep: bringing up
        Nav2 takes anywhere from a few seconds to half a minute depending on
        what else the robot is doing.
        """
        body: dict[str, Any] = {'mode': mode}
        if map_name:
            body['map'] = map_name
        result = self._post('/mode', body)
        if wait:
            self._wait(lambda: self.mode().get('mode') == mode, timeout,
                       f'mode did not become {mode!r}')
        return result

    def idle(self, **kw: Any) -> dict:
        return self.set_mode('idle', **kw)

    def start_mapping(self, **kw: Any) -> dict:
        return self.set_mode('mapping', **kw)

    def start_navigation(self, map_name: Optional[str] = None, **kw: Any) -> dict:
        return self.set_mode('navigation', map_name, **kw)

    # -- maps --------------------------------------------------------------

    def maps(self) -> list:
        return self._get('/maps')['maps']

    def current_map(self) -> Optional[str]:
        return self._get('/maps/current').get('current')

    def save_map(self, name: str, overwrite: bool = False) -> dict:
        return self._post('/maps', {'name': name, 'overwrite': overwrite})

    def delete_map(self, name: str) -> dict:
        return self._delete(f'/maps/{name}')

    def activate_map(self, name: str) -> dict:
        return self._post(f'/maps/{name}/activate')

    # -- waypoints ---------------------------------------------------------

    def waypoints(self, map_name: Optional[str] = None) -> list:
        return self._get('/waypoints', map=map_name)['waypoints']

    def waypoint(self, name: str, map_name: Optional[str] = None) -> dict:
        return self._get(f'/waypoints/{name}', map=map_name)['waypoint']

    def save_waypoint(self, name: str, x: Optional[float] = None,
                      y: Optional[float] = None, theta: float = 0.0,
                      type: str = 'waypoint',
                      map_name: Optional[str] = None) -> dict:
        """Save a waypoint. With no x/y, captures where the robot is now."""
        body: dict[str, Any] = {'name': name, 'type': type}
        if x is not None and y is not None:
            body.update({'x': x, 'y': y, 'theta': theta})
        if map_name:
            body['map'] = map_name
        return self._post('/waypoints', body)['waypoint']

    def delete_waypoint(self, name: str, map_name: Optional[str] = None) -> dict:
        return self._delete(f'/waypoints/{name}', map=map_name)

    # -- navigation --------------------------------------------------------

    def goto(self, waypoint: Optional[str] = None,
             x: Optional[float] = None, y: Optional[float] = None,
             theta: float = 0.0, replace: bool = False,
             wait: bool = False, timeout: float = 300.0) -> dict:
        """Send a navigation goal.

        Returns as soon as the robot accepts it. With wait=True, blocks until
        the goal reaches a terminal state and raises RobotError if that state
        is not 'succeeded' — so a failed drive is not silently mistaken for a
        completed one.
        """
        body: dict[str, Any] = {'replace': replace}
        if waypoint is not None:
            body['waypoint'] = waypoint
        elif x is not None and y is not None:
            body.update({'x': x, 'y': y, 'theta': theta})
        else:
            raise ValueError('provide either waypoint= or both x= and y=')

        result = self._post('/navigation/goto', body)
        if wait:
            final = self.wait_for_goal(timeout)
            if final['state'] != 'succeeded':
                raise RobotError('goal_' + final['state'],
                                 final.get('message') or f"goal {final['state']}",
                                 final, 0)
            return final
        return result

    def nav_status(self) -> dict:
        return self._get('/navigation/status')

    def cancel_goal(self) -> dict:
        return self._delete('/navigation/goal')

    def localize(self, x: float, y: float, theta: float = 0.0) -> dict:
        """Seed the pose estimate. A few tens of cm of accuracy is enough."""
        return self._post('/navigation/localize',
                          {'x': x, 'y': y, 'theta': theta})

    def path(self) -> list:
        return self._get('/navigation/path')['data']

    def wait_for_goal(self, timeout: float = 300.0,
                      poll: float = 1.0) -> dict:
        """Block until the navigation goal reaches a terminal state."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.nav_status()
            if status['state'] in NAV_DONE:
                return status
            time.sleep(poll)
        raise TimeoutError(f'goal did not finish within {timeout}s')

    def wait_for_localization(self, timeout: float = 60.0,
                              poll: float = 0.5) -> dict:
        """Block until the robot reports a map-frame pose."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            pose = self.pose()
            if pose.get('localized'):
                return pose
            time.sleep(poll)
        raise TimeoutError(f'robot did not localize within {timeout}s')

    # -- docking -----------------------------------------------------------

    def dock(self, navigate_to_staging: bool = True,
             wait: bool = False, timeout: float = 300.0) -> dict:
        """Dock on the charger.

        With wait=True, blocks until the battery reports charging — the only
        real proof of contact. Arriving and stopping are not evidence.
        """
        result = self._post('/dock',
                            {'navigate_to_staging': navigate_to_staging})
        if wait:
            return self.wait_for_charging(timeout)
        return result

    def undock(self, wait: bool = False, timeout: float = 120.0) -> dict:
        """Leave the charger and stop.

        Rarely needed: goto() undocks first, automatically.
        """
        result = self._post('/undock')
        if wait:
            self._wait(lambda: self.dock_status()['operation'] in DOCK_DONE,
                       timeout, 'undock did not finish')
            return self.dock_status()
        return result

    def dock_status(self) -> dict:
        return self._get('/dock/status')

    def dock_pose(self) -> dict:
        return self._get('/dock/pose')['data']

    def set_dock_pose(self, x: float, y: float, theta: float = 0.0) -> dict:
        return self._put('/dock/pose', {'x': x, 'y': y, 'theta': theta})

    def wait_for_charging(self, timeout: float = 300.0,
                          poll: float = 1.0) -> dict:
        """Block until charging starts, or the dock operation gives up."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.dock_status()
            if status.get('charging'):
                return status
            if status.get('operation') == 'failed':
                raise RobotError('dock_failed',
                                 status.get('message') or 'docking failed',
                                 status, 0)
            time.sleep(poll)
        raise TimeoutError(f'robot was not charging within {timeout}s')

    # -- motion ------------------------------------------------------------

    def velocity_command(self, linear: float = 0.0, angular: float = 0.0) -> dict:
        """One velocity command. Expires in ~0.5s — repeat at ~5Hz to keep moving."""
        return self._post('/motion/velocity',
                          {'linear': linear, 'angular': angular})

    def drive(self, linear: float = 0.0, angular: float = 0.0,
              duration: float = 1.0, rate: float = 5.0) -> None:
        """Hold a velocity for `duration` seconds, then stop.

        Repeats the command because a single one expires — that expiry is the
        safety property, so this helper honours it rather than working around
        it. It always stops at the end, including on exception.
        """
        interval = 1.0 / rate
        deadline = time.time() + duration
        try:
            while time.time() < deadline:
                self.velocity_command(linear, angular)
                time.sleep(interval)
        finally:
            self.stop()

    def stop(self) -> dict:
        """Zero velocity now. Does not cancel a navigation goal."""
        return self._post('/motion/stop')

    def move(self, distance: float, speed: float = 0.1) -> dict:
        """Drive a fixed distance in a straight line. Negative reverses."""
        return self._post('/motion/move',
                          {'distance': distance, 'speed': speed})

    def rotate(self, angle: float, speed: float = 0.3) -> dict:
        """Rotate in place by an angle in radians. Positive is counter-clockwise."""
        return self._post('/motion/rotate', {'angle': angle, 'speed': speed})

    # -- events ------------------------------------------------------------

    def events(self, streams: list, on_frame: Optional[Callable] = None
               ) -> Iterator[dict]:
        """Subscribe to the event stream and yield frames.

        Needs `websocket-client`. Yields every frame including `hello` and
        `error`, rather than filtering: a caller that never sees an error frame
        cannot react to a rejected subscription.
        """
        try:
            from websocket import create_connection
        except ImportError:
            raise RuntimeError(
                'events() needs websocket-client: pip install websocket-client')

        url = f'ws://{self.host}:{self.port}{API_PREFIX}/events'
        if self.token:
            url += f'?token={self.token}'

        ws = create_connection(url)
        try:
            ws.send(json.dumps({'action': 'subscribe', 'streams': streams}))
            while True:
                frame = json.loads(ws.recv())
                if on_frame is not None:
                    on_frame(frame)
                yield frame
        finally:
            ws.close()

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _wait(predicate: Callable[[], bool], timeout: float,
              what: str, poll: float = 0.5) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return
            time.sleep(poll)
        raise TimeoutError(f'{what} within {timeout}s')

    def __repr__(self) -> str:
        return f'NavProMini({self.host!r}, port={self.port})'
