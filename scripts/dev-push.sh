#!/usr/bin/env bash
set -euo pipefail

ip="${1:-}"
if [[ -z "$ip" ]]; then
  echo "Usage: ./scripts/dev-push.sh <DEVICE_IP>"
  exit 1
fi

if ! command -v balena >/dev/null 2>&1; then
  echo "balena CLI not found. Install with: npm i -g balena-cli && balena login"
  exit 1
fi

# Push the current workspace to the device for on-device build
balena push "$ip"