# Prerequiste

(1) Setup udev rules.

```shell
wget https://raw.githubusercontent.com/realsenseai/librealsense/refs/heads/master/config/99-realsense-libusb.rules
sudo cp 99-realsense-libusb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

(2) Install pixi

```shell
curl -fsSL https://pixi.sh/install.sh | sh
```

# Install

```shell
pixi install
```

# Test

```shell
# Test camera detection
pixi run rs-enumerate-devices
```

# Usage (one camera)
```shell
# (1) Terminal: Launch the camera
pixi run camera

# (2) Terminal: View camera images with crisp_py + matplotlib
pixi run test-image
```

`test-image` uses `CRISP_CONFIG_PATH=./crisp_configs` from Pixi activation and loads
`crisp_configs/cameras/realsense.yaml` through `crisp_py.make_camera("realsense")`.

# Usage (two-camera)

```shell
# (1) Terminal: Launch both RealSense cameras (color-only) with fixed serial numbers
#     and force an initial device reset for a clean start.
pixi run camera-dual

# (2) Terminal: View both streams in one matplotlib window
pixi run test-image-dual
```

`test-image-dual` loads:
- `crisp_configs/cameras/third_person.yaml`
- `crisp_configs/cameras/wrist.yaml`

Expected topics:
- `/third_person/color/image_raw`
- `/wrist/color/image_raw`

The launch task pins serial numbers with a leading underscore:
- `serial_no1:=_342522074350` (wrist)  <- Change yours serial number in pixi.toml
- `serial_no2:=_347622071856` (third_person)  <- Change yours serial number in pixi.toml

The `_` prefix is required by the realsense ROS2 wrapper to avoid numeric-string conversion issues.

To discover your serials:
```shell
pixi run rs-enumerate-devices
```

Use the `Serial Number` field from `rs-enumerate-devices`, not `Asic Serial Number`.

# Graceful exit and stale-process recovery

`Ctrl+C` is the correct way to stop both programs:
- `pixi run camera-dual`: wait until launch prints shutdown/clean exit lines.
- `pixi run test-image-dual`: `KeyboardInterrupt` is handled; window closes in `finally`.

If a camera appears stuck after exit, run:
```shell
# Stop any leftover RealSense ROS nodes/launchers
pkill -f realsense2_camera_node || true
pkill -f rs_multi_camera_launch.py || true

# Check no process still holds video devices
lsof /dev/video* 2>/dev/null
```

If needed, unplug/replug the camera USB cables.
