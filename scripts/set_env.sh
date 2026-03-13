#!/usr/bin/env bash

# Allow caller overrides while keeping sane defaults for this workspace.
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-100}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_zenoh_cpp}"
export ZENOH_SESSION_CONFIG_URI="${ZENOH_SESSION_CONFIG_URI:-./configs/zenoh_client.json5}"

# Keep ROS logs in a writable directory.
if [ -z "${ROS_LOG_DIR:-}" ]; then
  export ROS_LOG_DIR="${TMPDIR:-/tmp}/ros-log"
fi

mkdir -p "${ROS_LOG_DIR}"
