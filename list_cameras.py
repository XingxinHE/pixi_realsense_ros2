#!/usr/bin/env python3
"""Simple script to list connected RealSense cameras."""

import pyrealsense2 as rs


def main():
    context = rs.context()
    devices = context.query_devices()

    if len(devices) == 0:
        print("No RealSense cameras connected.")
        return

    print(f"Connected RealSense cameras: {len(devices)}")
    print()

    for i, device in enumerate(devices, 1):
        try:
            serial = device.get_info(rs.camera_info.serial_number)
            name = device.get_info(rs.camera_info.name)
            print(f"  Camera {i}:")
            print(f"    Name:   {name}")
            print(f"    Serial: {serial}")
        except RuntimeError as e:
            print(f"  Camera {i}:")
            print(f"    (Unable to query device info: {e})")


if __name__ == "__main__":
    main()
