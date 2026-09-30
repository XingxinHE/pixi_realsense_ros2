#!/usr/bin/env python3
"""Compare simultaneous camera-host and receiver CSVs by image header identity."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from camera_latency import distribution


def read_frames(path):
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    keys = [(r["topic"], r["frame_id"], int(r["stamp_ns"])) for r in rows]
    counts = Counter(keys)
    # Duplicate/zero timestamps are ambiguous; do not silently match them.
    return {k: int(r["receive_wall_ns"]) for k, r in zip(keys, rows)
            if counts[k] == 1 and k[2] > 0}, len(rows) - sum(v == 1 and k[2] > 0 for k, v in counts.items())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("local", type=Path, help="camera-host frames.csv")
    parser.add_argument("remote", type=Path, help="receiver frames.csv")
    parser.add_argument("--clocks-synchronized", action="store_true", required=True,
                        help="required: assert both host clocks have been checked")
    args = parser.parse_args()
    local, local_excluded = read_frames(args.local)
    remote, remote_excluded = read_frames(args.remote)
    result = {}
    for topic in sorted({k[0] for k in local.keys() | remote.keys()}):
        left = {k for k in local if k[0] == topic}
        right = {k for k in remote if k[0] == topic}
        matched = left & right
        result[topic] = {
            "matched_frames": len(matched),
            "local_unmatched_frames": len(left - right),
            "remote_unmatched_frames": len(right - left),
            "remote_minus_local_callback_ms": distribution(
                [(remote[k] - local[k]) / 1e6 for k in matched]),
        }
    print(json.dumps({"topics": result, "excluded_local_rows": local_excluded,
                      "excluded_remote_rows": remote_excluded,
                      "note": "Includes clock offset and differing subscriber scheduling; not wire-only latency. "
                              "Unmatched counts include non-overlapping windows, not just loss."}, indent=2))
    return 0 if any(r["matched_frames"] for r in result.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
