#!/usr/bin/env zsh
set -euo pipefail

cd "$(cd "$(dirname "$0")" && pwd)/.."

DMG_PATH=$(ls -1t dist/*.dmg 2> /dev/null | head -n 1 || true)
if [[ -z "$DMG_PATH" ]]; then
  echo "No DMG found in dist/. Run npm run build first."
  exit 1
fi

echo "Testing DMG: $DMG_PATH"

MOUNT_POINT=$(mktemp -d "/tmp/pomodoro-dmg-test.XXXXXX")
ATTACH_OUTPUT=$(hdiutil attach "$DMG_PATH" -readonly -mountpoint "$MOUNT_POINT" 2>&1)
EXIT_CODE=$?
if [[ $EXIT_CODE -ne 0 ]]; then
  echo "Failed to mount DMG:" >&2
  echo "$ATTACH_OUTPUT" >&2
  rm -rf "$MOUNT_POINT"
  exit $EXIT_CODE
fi

echo "Mounted at $MOUNT_POINT"
APP_PATH="$MOUNT_POINT/Pomodoro Syllabus.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "Expected app bundle not found at: $APP_PATH" >&2
  hdiutil detach "$MOUNT_POINT" >/dev/null 2>&1 || true
  rm -rf "$MOUNT_POINT"
  exit 1
fi

echo "App bundle found."

if [[ "${1:-}" == "--run" ]]; then
  echo "Opening app from mounted DMG..."
  open "$APP_PATH"
  echo "App launched. Keep the DMG mounted while testing, then close the app."
else
  echo "Run with --run to launch the app from the mounted DMG."
fi

echo "Detaching..."
hdiutil detach "$MOUNT_POINT" >/dev/null 2>&1
rm -rf "$MOUNT_POINT"
echo "DMG check passed."
