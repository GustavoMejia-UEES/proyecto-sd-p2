"""Discover local camera indexes without starting an Edge agent."""

import argparse
import json

import cv2


def discover(max_index: int, warmup: int) -> list[dict]:
    cameras = []
    for index in range(max_index + 1):
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            capture = cv2.VideoCapture(index)
        try:
            if not capture.isOpened():
                continue
            frame = None
            ok = False
            for _ in range(max(1, warmup)):
                ok, frame = capture.read()
                if ok:
                    break
            cameras.append(
                {
                    "source": str(index),
                    "available": bool(ok),
                    "width": int(frame.shape[1]) if ok else None,
                    "height": int(frame.shape[0]) if ok else None,
                    "backend": capture.getBackendName(),
                }
            )
        finally:
            capture.release()
    return cameras


def main():
    parser = argparse.ArgumentParser(description="Discover Windows camera indexes")
    parser.add_argument("--max-index", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=3)
    args = parser.parse_args()
    max_index = max(0, min(args.max_index, 10))
    print(json.dumps(discover(max_index, args.warmup), indent=2))


if __name__ == "__main__":
    main()
