#!/usr/bin/env bash
set -euo pipefail

PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
  wait || true
}

trap cleanup EXIT INT TERM

launch_camera() {
  local name="$1"
  local serial="$2"

  ros2 launch realsense2_camera rs_launch.py \
    camera_namespace:=/ \
    camera_name:="${name}" \
    serial_no:="_${serial}" \
    initial_reset:=true \
    enable_depth:=false \
    rgb_camera.color_profile:=640x480x30 &

  PIDS+=("$!")
}

launch_camera "robot0_agentview_left" "342522074350"
launch_camera "robot0_agentview_right" "347622071856"
launch_camera "robot0_eye_in_hand" "336222070633"

wait
