#!/usr/bin/env bash
set -euo pipefail

ip="${1:-}"
if [[ -z "$ip" ]]; then
  echo "Usage: ./scripts/dev-logs.sh <DEVICE_IP>"
  exit 1
fi

if ! command -v balena >/dev/null 2>&1; then
  echo "balena CLI not found. Install with: npm i -g balena-cli && balena login"
  exit 1
fi

# Follow service logs for quick iteration
balena logs "$ip" --service clock --follow