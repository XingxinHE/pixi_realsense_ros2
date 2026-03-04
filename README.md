# Prerequiste

```shell
wget https://raw.githubusercontent.com/realsenseai/librealsense/refs/heads/master/config/99-realsense-libusb.rules
sudo cp 99-realsense-libusb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```


# Install

```shell
pixi install
```

# Test

```shell
# Test camera detection
pixi run rs-enumerate-devices

# Launch the camera
pixi run ros2 launch realsense2_camera rs_launch.py
```