#!/usr/bin/env bash
# Run QwenCloud auto-register on a hidden virtual display.
# Browser stays headed (better Cloudflare bypass) but no real window appears.

set -e

# Pick a free display number; default :99 is unlikely to be a real monitor.
DISP="${QWENCLOUD_DISPLAY:-:99}"

# Start Xvfb if not already running on the chosen display.
if ! xdpyinfo -display "${DISP}" >/dev/null 2>&1; then
    echo "[xvfb] starting virtual display ${DISP}..."
    Xvfb "${DISP}" -screen 0 1366x768x24 +extension RANDR >/dev/null 2>&1 &
    XVFB_PID=$!
    sleep 2
    # Clean up Xvfb on exit.
    trap 'kill "${XVFB_PID}" 2>/dev/null || true' EXIT
fi

# Run the bot on the virtual display.
# QWENCLOUD_HIDDEN tells run.py it is already inside the wrapper so Playwright
# stays headed (better CF bypass) instead of real headless.
export QWENCLOUD_HIDDEN=1
# Force Chromium to use X11 backend so Xvfb captures it instead of opening a
# real window on the host Wayland compositor (Hyprland).
unset WAYLAND_DISPLAY
export XDG_SESSION_TYPE=x11
export DISPLAY="${DISP}"
python3 run.py "$@"
