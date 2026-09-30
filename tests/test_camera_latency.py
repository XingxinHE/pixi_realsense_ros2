import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from camera_latency import FIELDS, distribution, summarize
from compare_latency import read_frames


class MetricsTest(unittest.TestCase):
    def test_percentiles_and_empty(self):
        self.assertIsNone(distribution([]))
        self.assertEqual(distribution([4, 1, 3, 2])["p50"], 2.5)
        self.assertEqual(distribution([5])["p99"], 5)

    def test_stalls_and_clock_errors_remain_visible(self):
        rows = [dict(stamp_ns=2_000_000_000, receive_wall_ns=1_990_000_000,
                     receive_mono_ns=1_000_000_000, payload_bytes=100)]
        result = summarize(rows, 0, 5_000_000_000)
        self.assertEqual(result["fps"], .2)
        self.assertEqual(result["negative_age_frames"], 1)
        self.assertEqual(result["header_age_ms"]["p50"], -10)
        self.assertEqual(result["arrival_gap_ms_including_window_edges"]["max"], 4000)

    def test_duplicate_and_zero_stamps_excluded_from_join(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frames.csv"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=FIELDS)
                writer.writeheader()
                for stamp in [0, 1, 1, 2]:
                    writer.writerow(dict(topic="/test", frame_id="camera", stamp_ns=stamp,
                                         receive_wall_ns=123, receive_mono_ns=456, payload_bytes=10))
            frames, excluded = read_frames(path)
            self.assertEqual(frames, {("/test", "camera", 2): 123})
            self.assertEqual(excluded, 3)


@unittest.skipUnless(os.getenv("RUN_ROS_TESTS") == "1", "set RUN_ROS_TESTS=1 inside pixi")
class RosIntegrationTest(unittest.TestCase):
    def test_three_streams_and_missing_topic(self):
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import Image

        rclpy.init(args=[])
        node = Node("latency_test_publisher")
        topics = [f"/latency_test_{os.getpid()}/camera_{i}" for i in range(3)]
        publishers = [node.create_publisher(Image, t, qos_profile_sensor_data) for t in topics]
        try:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "run"
                command = [sys.executable, str(ROOT / "scripts/camera_latency.py"),
                           "--topics", *topics, "--duration", "2", "--warmup", "1",
                           "--output", str(output)]
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    deadline = time.monotonic() + 15
                    while process.poll() is None and time.monotonic() < deadline:
                        msg = Image(height=480, width=640, encoding="rgb8", step=640 * 3)
                        msg.header.frame_id = "synthetic"
                        stamp = time.time_ns() - 20_000_000
                        msg.header.stamp.sec, msg.header.stamp.nanosec = divmod(stamp, 1_000_000_000)
                        msg.data = bytes(640 * 480 * 3)
                        for pub in publishers:
                            pub.publish(msg)
                        time.sleep(1 / 30)
                    stdout, stderr = process.communicate(timeout=3)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.communicate()
                self.assertEqual(process.returncode, 0, stdout + stderr)
                summary = json.loads((output / "summary.json").read_text())
                self.assertEqual(summary["age_clock_status"], "UNVERIFIED")
                for result in summary["topics"].values():
                    self.assertGreater(result["frames"], 10)
                    self.assertGreaterEqual(result["header_age_ms"]["min"], 20)
                    self.assertGreater(result["payload_mbit_s"], 0)
                shifted = Path(directory) / "shifted.csv"
                with (output / "frames.csv").open(newline="") as stream:
                    shifted_rows = list(csv.DictReader(stream))
                with shifted.open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=FIELDS)
                    writer.writeheader()
                    for row in shifted_rows:
                        row["receive_wall_ns"] = int(row["receive_wall_ns"]) + 7_000_000
                        writer.writerow(row)
                comparison = subprocess.run(
                    [sys.executable, str(ROOT / "scripts/compare_latency.py"),
                     str(output / "frames.csv"), str(shifted), "--clocks-synchronized"],
                    capture_output=True, text=True, timeout=5)
                self.assertEqual(comparison.returncode, 0, comparison.stderr)
                compared = json.loads(comparison.stdout)
                for result in compared["topics"].values():
                    self.assertGreater(result["matched_frames"], 10)
                    self.assertEqual(result["remote_minus_local_callback_ms"]["max"], 7)
                missing = subprocess.run(
                    [sys.executable, str(ROOT / "scripts/camera_latency.py"),
                     "--topics", "/latency_test_absent", "--warmup", ".1", "--duration", ".2",
                     "--output", str(Path(directory) / "missing")],
                    capture_output=True, text=True, timeout=10)
                self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
        finally:
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    unittest.main()
