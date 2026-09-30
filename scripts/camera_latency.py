#!/usr/bin/env python3
"""Measure application-visible image delivery; save metadata, never image pixels."""

import argparse
import csv
import json
import math
import os
from pathlib import Path
import socket
import time


DEFAULT_TOPICS = [f"/{name}/color/image_raw" for name in (
    "robot0_agentview_left", "robot0_agentview_right", "robot0_eye_in_hand")]
FIELDS = ("topic", "frame_id", "stamp_ns", "receive_wall_ns", "receive_mono_ns",
          "payload_bytes")


def distribution(values):
    values = sorted(values)
    if not values:
        return None

    def percentile(p):
        index = (len(values) - 1) * p
        lo = int(index)
        hi = math.ceil(index)
        return values[lo] + (values[hi] - values[lo]) * (index - lo)

    return dict(zip(("min", "p50", "p95", "p99", "max"),
                    (values[0], percentile(.5), percentile(.95),
                     percentile(.99), values[-1])))


def summarize(rows, start_ns, end_ns):
    seconds = max((end_ns - start_ns) / 1e9, 1e-9)
    ages = [(r["receive_wall_ns"] - r["stamp_ns"]) / 1e6
            for r in rows if r["stamp_ns"] > 0]
    arrivals = [start_ns] + [r["receive_mono_ns"] for r in rows] + [end_ns]
    gaps = [(b - a) / 1e6 for a, b in zip(arrivals, arrivals[1:])]
    stamps = [r["stamp_ns"] for r in rows]
    return {
        "frames": len(rows), "fps": len(rows) / seconds,
        "payload_mbit_s": sum(r["payload_bytes"] for r in rows) * 8 / seconds / 1e6,
        "header_age_ms": distribution(ages),
        "negative_age_frames": sum(age < 0 for age in ages),
        "invalid_stamp_frames": sum(stamp <= 0 for stamp in stamps),
        "duplicate_stamps": len(stamps) - len(set(stamps)),
        "backward_stamp_steps": sum(b < a for a, b in zip(stamps, stamps[1:])),
        "arrival_gap_ms_including_window_edges": distribution(gaps),
    }


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be finite and greater than zero")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topics", nargs="+", default=DEFAULT_TOPICS)
    parser.add_argument("--transport", choices=("raw", "compressed"), default="raw",
                        help="compressed appends /compressed to each base topic")
    parser.add_argument("--duration", type=positive, default=60, help="measurement seconds")
    parser.add_argument("--warmup", type=positive, default=5, help="discard initial seconds")
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--reliability", choices=("best-effort", "reliable"), default="best-effort")
    parser.add_argument("--clocks-synchronized", action="store_true",
                        help="assert host clocks have been synchronized and checked")
    parser.add_argument("--label", default="unlabelled")
    parser.add_argument("--output", type=Path, default=Path("results") / time.strftime("%Y%m%d-%H%M%S"))
    args = parser.parse_args()
    if args.depth < 1 or len(set(args.topics)) != len(args.topics):
        parser.error("depth must be positive and topics must be unique")
    # Refuse to overwrite an earlier experiment, before creating ROS entities.
    args.output.mkdir(parents=True, exist_ok=False)

    import rclpy
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
    from rclpy.utilities import get_rmw_implementation_identifier
    from sensor_msgs.msg import Image, CompressedImage

    rclpy.init(args=[])
    node = Node("camera_latency", enable_rosout=False)
    qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST, depth=args.depth,
        reliability=(ReliabilityPolicy.BEST_EFFORT if args.reliability == "best-effort"
                     else ReliabilityPolicy.RELIABLE), durability=DurabilityPolicy.VOLATILE)
    topics = [t + "/compressed" if args.transport == "compressed" else t for t in args.topics]
    rows = {topic: [] for topic in topics}
    started_wall_ns = time.time_ns()
    start_ns = time.monotonic_ns() + int(args.warmup * 1e9)
    deadline_ns = start_ns + int(args.duration * 1e9)

    def callback(topic):
        def receive(msg):
            wall_ns = time.time_ns()
            mono_ns = time.monotonic_ns()
            if start_ns <= mono_ns < deadline_ns:
                rows[topic].append(dict(zip(FIELDS, (
                    topic, msg.header.frame_id,
                    msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec,
                    wall_ns, mono_ns, len(msg.data)))))
        return receive

    for topic in topics:
        node.create_subscription(Image if args.transport == "raw" else CompressedImage,
                                 topic, callback(topic), qos)
    metadata = {
        "label": args.label, "host": socket.gethostname(),
        "started_wall_ns": started_wall_ns,
        "rmw": get_rmw_implementation_identifier(),
        "environment": {key: os.getenv(key) for key in (
            "ROS_DOMAIN_ID", "ROS_NETWORK_INTERFACE", "CYCLONEDDS_URI", "ZENOH_SESSION_CONFIG_URI")},
        "settings": {key: str(value) if isinstance(value, Path) else value
                     for key, value in vars(args).items()},
        "age_clock_status": "user-verified" if args.clocks_synchronized else "UNVERIFIED",
    }
    print(f"Warmup {args.warmup}s; measuring {args.duration}s; {metadata['rmw']}", flush=True)
    print("Header age includes camera/driver, transport, deserialization and executor delay. "
          "Cross-host ages require verified clock synchronization.", flush=True)
    next_report_ns = start_ns + 5_000_000_000
    interrupted = False
    try:
        while rclpy.ok() and time.monotonic_ns() < deadline_ns:
            rclpy.spin_once(node, timeout_sec=.1)
            now = time.monotonic_ns()
            if now >= next_report_ns:
                print("Received: " + ", ".join(f"{t}: {len(rs)}" for t, rs in rows.items()), flush=True)
                next_report_ns = now + 5_000_000_000
    except (KeyboardInterrupt, ExternalShutdownException):
        interrupted = True
    finally:
        end_ns = max(start_ns, min(time.monotonic_ns(), deadline_ns))
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        with (args.output / "frames.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            for topic_rows in rows.values():
                writer.writerows(topic_rows)
        metadata.update(measured_seconds=(end_ns - start_ns) / 1e9, interrupted=interrupted,
                        topics={t: summarize(rs, start_ns, end_ns) for t, rs in rows.items()})
        (args.output / "summary.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(json.dumps(metadata["topics"], indent=2))
        print(f"Saved {args.output}/frames.csv and summary.json")
    missing = [topic for topic, samples in rows.items() if not samples]
    if missing:
        print("ERROR: no measured frames for " + ", ".join(missing))
    return 2 if missing else (130 if interrupted else 0)


if __name__ == "__main__":
    raise SystemExit(main())
