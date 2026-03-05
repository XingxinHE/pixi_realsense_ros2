"""Display two RealSense camera streams with crisp_py in one window."""

import time

import matplotlib.pyplot as plt
from crisp_py.camera import make_camera


READY_TIMEOUT_SEC = 20.0
REFRESH_HZ = 30.0

# Prevent the plotting backend from repeatedly raising the window to front.
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
    third_person_camera = _load_camera("third_person")
    wrist_camera = _load_camera("wrist")

    plt.ion()
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    plt.show(block=False)

    third_person_axis, wrist_axis = axes
    third_person_axis.set_title("Third Person")
    wrist_axis.set_title("Wrist")
    third_person_axis.axis("off")
    wrist_axis.axis("off")

    third_person_plot = third_person_axis.imshow(third_person_camera.current_image)
    wrist_plot = wrist_axis.imshow(wrist_camera.current_image)

    try:
        while True:
            third_person_plot.set_data(third_person_camera.current_image)
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
