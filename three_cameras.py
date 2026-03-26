"""Display three RealSense camera streams with crisp_py in one window."""

import time

import matplotlib.pyplot as plt
from crisp_py.camera import make_camera


READY_TIMEOUT_SEC = 20.0
REFRESH_HZ = 30.0

plt.rcParams["figure.raise_window"] = False


def _load_camera(config_name: str):
    camera = make_camera(config_name)
    try:
        camera.wait_until_ready(timeout=READY_TIMEOUT_SEC)
    except TimeoutError as exc:
        raise RuntimeError(
            f"Timed out waiting for '{config_name}' camera stream. "
            f"Make sure the corresponding RealSense node is running and publishing to "
            f"{camera.config.camera_color_image_topic}/compressed."
        ) from exc
    return camera


def main() -> None:
    left_camera = _load_camera("robot0_agentview_left")
    right_camera = _load_camera("robot0_agentview_right")
    wrist_camera = _load_camera("robot0_eye_in_hand")

    plt.ion()
    figure, axes = plt.subplots(1, 3, figsize=(15, 5))
    plt.show(block=False)

    left_axis, right_axis, wrist_axis = axes
    left_axis.set_title("robot0_agentview_left")
    right_axis.set_title("robot0_agentview_right")
    wrist_axis.set_title("robot0_eye_in_hand")

    left_axis.axis("off")
    right_axis.axis("off")
    wrist_axis.axis("off")

    left_plot = left_axis.imshow(left_camera.current_image)
    right_plot = right_axis.imshow(right_camera.current_image)
    wrist_plot = wrist_axis.imshow(wrist_camera.current_image)

    try:
        while True:
            left_plot.set_data(left_camera.current_image)
            right_plot.set_data(right_camera.current_image)
            wrist_plot.set_data(wrist_camera.current_image)
            figure.canvas.draw_idle()
            figure.canvas.flush_events()
            time.sleep(1.0 / REFRESH_HZ)
    except KeyboardInterrupt:
        pass
    finally:
        plt.close(figure)


if __name__ == "__main__":
    main()
