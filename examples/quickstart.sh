#!/usr/bin/env bash
# Every read-only endpoint, in order. Changes nothing on the robot.
set -euo pipefail

HOST="${ROBOT_HOST:-192.168.1.50}"
ROBOT="http://${HOST}:8090/api/v1"
AUTH=()
[ -n "${ROBOT_TOKEN:-}" ] && AUTH=(-H "Authorization: Bearer ${ROBOT_TOKEN}")

get() {
  printf '\n\033[1;36m── GET %s\033[0m\n' "$1"
  curl -s --max-time 10 "${AUTH[@]}" "${ROBOT}$1" | python3 -m json.tool || echo "(failed)"
}

printf '\033[1mNavProMini SDK — %s\033[0m\n' "$ROBOT"

get /system/info
get /system/health
get /state/pose
get /state/velocity
get /state/battery
get /state/temperature
get /mode
get /maps
get /maps/current
get /waypoints
get /navigation/status
get /dock/status

# Scan is ~720 numbers; summarize instead of dumping it.
printf '\n\033[1;36m── GET /state/scan (summary)\033[0m\n'
curl -s --max-time 10 "${AUTH[@]}" "${ROBOT}/state/scan" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)["data"]
except Exception:
    print("(no scan data)"); raise SystemExit
hits = [r for r in d["ranges"] if r is not None]
print("%d beams, %d returns" % (d["count"], len(hits)))
if hits:
    print("nearest %.3f m, farthest %.3f m" % (min(hits), max(hits)))
'

printf '\n\033[1;32mdone\033[0m\n'
