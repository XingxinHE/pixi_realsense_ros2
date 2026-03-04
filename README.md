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
pixi run camera

# In another terminal, view camera images with crisp_py + matplotlib
pixi run test-image
```

`test-image` sets `CRISP_CONFIG_PATH` to `./crisp_configs` and loads
`crisp_configs/cameras/realsense.yaml` through `crisp_py.make_camera("realsense")`.
