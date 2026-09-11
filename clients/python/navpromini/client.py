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
MISSION_DONE = ('completed', 'failed', 'canceled')


class RobotError(Exception):
    """A typed error from the robot.

    Carries the server's `code` so callers can branch on it. The message is for
    humans and may change between versions; the code will not.
    """

    def __init__(self, code: str, message: str,
                 detail: Optional[dict] = None, status: int = 400) -> None:
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

    def lifecycle(self) -> dict:
        """System lifecycle state, current phase, and subsystem readiness."""
        return self._get('/system/lifecycle')

    # -- state -------------------------------------------------------------
    #
    # These unwrap `data` and drop `age_sec`, because the common case is
    # "give me the reading". Anything that needs the age uses state_raw().

    def robot_state(self) -> dict:
        """The canonical full Robot State (§18): {robot, lifecycle, mode,
        connection, hardware, battery, map, localization, navigation, mission, dock, error}.
        """
        return self._get('/state')

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

    def finish_mapping(self, name: str) -> dict:
        """Save the SLAM map under `name` and transition back to idle mode."""
        return self._post('/mapping/finish', {'name': name})

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

    def current_map_info(self) -> dict:
        """Dimensions, resolution, and origin metadata of the active map."""
        return self._get('/maps/current/info')

    def current_map_image(self, rotate: int = 0) -> bytes:
        """Fetch the active map rendered directly as a PNG image.

        Args:
            rotate: Rotation angle in degrees (0, 90, 180, 270).

        Returns:
            Raw PNG image bytes.
        """
        params = {'rotate': rotate} if rotate else None
        response = self._session.get(f'{self.base}/maps/current/image',
                                     params=params, timeout=self.timeout)
        if not response.ok:
            raise RobotError('image_fetch_failed',
                             response.text[:200] or response.reason,
                             {}, response.status_code)
        return response.content

    def current_map_raw(self) -> bytes:
        """Raw binary RGB565 buffer of the active map with header."""
        response = self._session.get(f'{self.base}/maps/current/raw', timeout=self.timeout)
        if not response.ok:
            raise RobotError('raw_map_failed',
                             response.text[:200] or response.reason,
                             {}, response.status_code)
        return response.content

    def save_map(self, name: str, overwrite: bool = False) -> dict:
        return self._post('/maps', {'name': name, 'overwrite': overwrite})

    def delete_map(self, name: str) -> dict:
        return self._delete(f'/maps/{name}')

    def activate_map(self, name: str) -> dict:
        return self._post(f'/maps/{name}/activate')

    # -- waypoints ---------------------------------------------------------

    def waypoints(self, map_name: Optional[str] = None, map: Optional[str] = None) -> list:
        return self._get('/waypoints', map=map_name or map)['waypoints']

    def waypoint(self, name: str, map_name: Optional[str] = None, map: Optional[str] = None) -> dict:
        return self._get(f'/waypoints/{name}', map=map_name or map)['waypoint']

    def save_waypoint(self, name: str, x: Optional[float] = None,
                      y: Optional[float] = None, theta: float = 0.0,
                      type: str = 'waypoint',
                      map_name: Optional[str] = None,
                      map: Optional[str] = None) -> dict:
        """Save a waypoint. With no x/y, captures where the robot is now."""
        body: dict[str, Any] = {'name': name, 'type': type}
        if x is not None and y is not None:
            body.update({'x': x, 'y': y, 'theta': theta})
        target_map = map_name or map
        if target_map:
            body['map'] = target_map
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

    def global_relocalize(self) -> dict:
        """Disperse AMCL particles across the map for global relocalization."""
        return self._post('/navigation/relocalize/global')

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

    def cancel_dock(self) -> dict:
        """Cancel an in-progress docking or undocking operation."""
        return self._delete('/dock/goal')

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

    # -- missions ----------------------------------------------------------

    def missions(self, map: Optional[str] = None, map_name: Optional[str] = None) -> list:
        """List all saved missions, optionally filtered by map."""
        return self._get('/missions', map=map_name or map)['missions']

    def mission(self, id: str) -> dict:
        """Fetch a single mission by id."""
        return self._get(f'/missions/{id}')['mission']

    def save_mission(self, id: Union[str, dict], steps: Optional[list[dict]] = None,
                     name: Optional[str] = None, loop_count: int = 1,
                     loop_forever: bool = False, map: Optional[str] = None,
                     map_name: Optional[str] = None) -> dict:
        """Create or replace a mission by id or config dict.

        Args:
            id: Unique identifier for the mission (str), or a complete mission dict.
            steps: List of step dicts (required if id is a string):
                - navigate: {'type': 'navigate', 'waypoint': 'station_a'} (or {'target': 'station_a'} or {'x': 1.0, 'y': 2.0, 'theta': 0.0})
                - wait: {'type': 'wait', 'duration': 5.0} (or duration_sec)
                - dock: {'type': 'dock', 'navigate_to_staging': True}
                - undock: {'type': 'undock'}
                - call_service: {'type': 'call_service', 'service': '/camera/capture', 'service_type': 'std_srvs/srv/Trigger', 'request': {...}, 'timeout': 15.0, 'ignore_error': False}
                - call_action: {'type': 'call_action', 'action': '/spin', 'action_type': 'nav2_msgs/action/Spin', 'goal': {...}, 'timeout': 300.0, 'ignore_error': False}
                - call_api: {'type': 'call_api', 'url': 'https://mes.local/api', 'method': 'POST', 'payload': {...}, 'headers': {...}, 'timeout': 15.0, 'ignore_error': False}
            name: Optional human-readable name (defaults to id).
            loop_count: Repeat count for the entire sequence (default 1).
            loop_forever: Repeat indefinitely until canceled (default False).
            map: Optional map name to bind the mission to (defaults to active map on robot).
            map_name: Alias for map parameter.
        """
        target_map = map_name or map
        if isinstance(id, dict):
            data = id
            mission_id = str(data.get('id') or data.get('name') or '')
            if 'nodes' in data:
                body: dict[str, Any] = {
                    'id': mission_id,
                    'name': data.get('name', mission_id),
                    'type': 'graph',
                    'nodes': data['nodes'],
                    'edges': data.get('edges', []),
                }
                if 'entrypoint' in data:
                    body['entrypoint'] = data['entrypoint']
                if 'map' in data or target_map:
                    body['map'] = data.get('map', target_map)
                if 'settings' in data:
                    body['settings'] = data['settings']
                return self._post('/missions', body)['mission']

            mission_steps = data.get('steps') or steps or []
            if not mission_steps and 'tasks' in data:
                mission_steps = []
                for t in data['tasks']:
                    if t.get('waypoint'):
                        mission_steps.append({'type': 'navigate', 'target': t['waypoint']})
                    act = t.get('action')
                    params = t.get('params') or {}
                    if act == 'wait':
                        mission_steps.append({'type': 'wait', 'duration': params.get('duration_sec', params.get('duration', 5.0))})
                    elif act == 'dock':
                        mission_steps.append({'type': 'dock', 'navigate_to_staging': params.get('navigate_to_staging', True)})
                    elif act == 'undock':
                        mission_steps.append({'type': 'undock'})
                    elif act == 'call_service':
                        mission_steps.append({'type': 'call_service', **params})
                    elif act == 'call_action':
                        mission_steps.append({'type': 'call_action', **params})
                    elif act == 'call_api':
                        mission_steps.append({'type': 'call_api', **params})
            m_name = data.get('name', mission_id)
            l_count = data.get('loop_count', loop_count)
            l_forever = data.get('loop_forever', data.get('loop', loop_forever))
            map_val = data.get('map', target_map)
            body = {
                'id': mission_id,
                'steps': mission_steps,
                'loop_count': l_count,
                'loop_forever': l_forever,
            }
            if m_name:
                body['name'] = m_name
            if map_val:
                body['map'] = map_val
            return self._post('/missions', body)['mission']

        if steps is None:
            raise ValueError("steps list is required when id is a string")

        body = {
            'id': id,
            'steps': steps,
            'loop_count': loop_count,
            'loop_forever': loop_forever,
        }
        if name:
            body['name'] = name
        if target_map:
            body['map'] = target_map
        return self._post('/missions', body)['mission']

    def save_graph_mission(self, id: str, nodes: list[dict], edges: Optional[list[dict]] = None,
                           name: Optional[str] = None, entrypoint: Optional[str] = None,
                           map: Optional[str] = None, settings: Optional[dict] = None) -> dict:
        """Create or replace a visual node-based mission graph."""
        body: dict[str, Any] = {
            'id': id,
            'name': name or id,
            'type': 'graph',
            'nodes': nodes,
            'edges': edges or [],
        }
        if entrypoint:
            body['entrypoint'] = entrypoint
        if map:
            body['map'] = map
        if settings:
            body['settings'] = settings
        return self._post('/missions', body)['mission']

    def get_mission_node_types(self) -> dict:
        """Fetch the available visual node types catalog from the robot engine."""
        return self._get('/missions/node_types')

    def get_active_ui_interaction(self) -> Optional[dict]:
        """Fetch any currently active UI interaction prompt if mission is waiting."""
        res = self._get('/missions/active_ui_interaction')
        return res.get('active_interaction') or res.get('interaction')

    def respond_to_ui_interaction(self, interaction_id: str, action: str = 'submit',
                                  selected: Optional[str] = None, form_data: Optional[dict] = None,
                                  **kwargs) -> dict:
        """Submit user/agent response to an active Human-in-the-Loop interaction."""
        body: dict[str, Any] = {
            'interaction_id': interaction_id,
            'action': action,
        }
        if selected is not None:
            body['selected'] = selected
        if form_data is not None:
            body['form_data'] = form_data
        body.update(kwargs)
        return self._post('/missions/ui_response', body)

    def delete_mission(self, id: str) -> dict:
        """Delete a saved mission by id."""
        return self._delete(f'/missions/{id}')

    def start_mission(self, id: str, wait: bool = False,
                      timeout: float = 600.0) -> dict:
        """Start running a saved mission. Returns 202 accepted immediately.

        With wait=True, blocks until the mission completes, fails, or is canceled.
        """
        result = self._post(f'/missions/{id}/start')
        if wait:
            return self.wait_for_mission(id=id, timeout=timeout)
        return result

    def pause_mission(self, id: Optional[str] = None) -> dict:
        """Pause a running mission after the currently executing step."""
        mid = id or self.mission_status().get('mission_id')
        if not mid:
            raise RobotError('no_active_mission', 'No active mission to pause', {}, 400)
        return self._post(f'/missions/{mid}/pause')

    def resume_mission(self, id: Optional[str] = None) -> dict:
        """Resume a paused mission. Also overrides low-battery auto-dock."""
        mid = id or self.mission_status().get('mission_id')
        if not mid:
            raise RobotError('no_active_mission', 'No active mission to resume', {}, 400)
        return self._post(f'/missions/{mid}/resume')

    def cancel_mission(self, id: Optional[str] = None) -> dict:
        """Stop and cancel a running or paused mission permanently."""
        mid = id or self.mission_status().get('mission_id')
        if not mid:
            raise RobotError('no_active_mission', 'No active mission to cancel', {}, 400)
        return self._post(f'/missions/{mid}/cancel')

    def mission_status(self) -> dict:
        """Current status of the active mission runner robot-wide."""
        return self._get('/missions/status')

    def wait_for_mission(self, id: Optional[str] = None,
                         timeout: float = 600.0,
                         poll: float = 1.0) -> dict:
        """Block until the mission reaches a terminal state (completed, failed, canceled).

        Raises RobotError if the mission fails, or TimeoutError on timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.mission_status()
            if status['state'] in MISSION_DONE:
                if status['state'] == 'failed':
                    raise RobotError('mission_failed',
                                     status.get('message') or 'mission failed',
                                     status, 0)
                return status
            time.sleep(poll)
        raise TimeoutError(f'mission did not finish within {timeout}s')

    # -- schedules ---------------------------------------------------------

    def schedules(self) -> list:
        """List all configured schedules."""
        return self._get('/schedules')['schedules']

    def schedule(self, id: str) -> dict:
        """Fetch a single schedule by id."""
        return self._get(f'/schedules/{id}')['schedule']

    def save_schedule(self, id: str, mission_id: str,
                      hour: int, minute: int, repeat: str = 'daily',
                      name: Optional[str] = None,
                      date: Optional[str] = None,
                      enabled: bool = True) -> dict:
        """Create or replace a scheduled mission trigger.

        Args:
            id: Unique identifier for the schedule.
            mission_id: The ID of the saved mission to execute.
            hour: Hour of the day in 24h format (0-23).
            minute: Minute of the hour (0-59).
            repeat: Recurrence rule ('daily', 'weekly', or 'once').
            name: Optional human-readable name.
            date: 'YYYY-MM-DD' (required when repeat is 'once').
            enabled: Whether the schedule is active (default True).
        """
        body: dict[str, Any] = {
            'id': id,
            'mission_id': mission_id,
            'hour': hour,
            'minute': minute,
            'repeat': repeat,
            'enabled': enabled,
        }
        if name:
            body['name'] = name
        if date:
            body['date'] = date
        return self._post('/schedules', body)['schedule']

    def delete_schedule(self, id: str) -> dict:
        """Delete a schedule by id."""
        return self._delete(f'/schedules/{id}')

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
