#!/usr/bin/env bash
set -euo pipefail
url="${1:?usage: smoke.sh https://your-service}"
body="$(curl -fsS --max-time 90 "$url/health")"
echo "$body"
echo "$body" | grep -q '"status":"ok"'
