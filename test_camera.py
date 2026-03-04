import matplotlib.pyplot as plt
from crisp_py.camera import make_camera


def main() -> None:
    camera = make_camera("realsense")
    camera.wait_until_ready(timeout=20.0)

    plt.ion()
    figure, axis = plt.subplots()
    axis.axis("off")
    image_plot = axis.imshow(camera.current_image)

    try:
        while True:
            image_plot.set_data(camera.current_image)
            plt.pause(1.0 / 30.0)
    except KeyboardInterrupt:
        pass
    finally:
        plt.close(figure)


if __name__ == "__main__":
    main()