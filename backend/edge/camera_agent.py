"""ARGUS Edge camera agent."""

import os
import threading
import time
from datetime import datetime, timezone
from typing import Generator

import cv2
import requests
from fastapi import FastAPI
from fastapi.responses import StreamingResponse


def env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


CORE_API_URL = os.getenv("CORE_API_URL", "http://localhost:8000").rstrip("/")
CAMERA_ID = os.getenv("CAMERA_ID", "CAM-EDGE-01")
CAMERA_NAME = os.getenv("CAMERA_NAME", "ARGUS Edge Camera")
CAMERA_TYPE = os.getenv("CAMERA_TYPE", "usb")
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0")
EDGE_STREAM_URL = os.getenv("EDGE_STREAM_URL", "http://localhost:8081/stream")
IOT_SEGMENT = os.getenv("IOT_SEGMENT", "iot-cameras")
MOTION_ENABLED = env_bool("MOTION_ENABLED", True)
MOTION_THRESHOLD = float(os.getenv("MOTION_THRESHOLD", "18"))
MOTION_COOLDOWN_SECONDS = int(os.getenv("MOTION_COOLDOWN_SECONDS", "5"))
VISION_MODE = os.getenv("VISION_MODE", "motion").lower()
DETECTION_ENABLED = env_bool("DETECTION_ENABLED", VISION_MODE == "cctv")
DETECTION_INTERVAL = max(1, int(os.getenv("DETECTION_INTERVAL", "3")))
DETECTION_CONFIDENCE = float(os.getenv("DETECTION_CONFIDENCE", "0.45"))
DETECTION_MODEL = os.getenv("DETECTION_MODEL", "yolo11n.pt")
DETECTION_CLASSES = {
    int(value.strip())
    for value in os.getenv("DETECTION_CLASSES", "").split(",")
    if value.strip().isdigit()
}

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


def camera_source():
    return int(CAMERA_SOURCE) if CAMERA_SOURCE.isdigit() else CAMERA_SOURCE


class CameraAgent:
    def __init__(self):
        self.capture = None
        self.running = False
        self.status = "offline"
        self.fps = 0.0
        self.last_frame = None
        self.frame_condition = threading.Condition()
        self.worker = None
        self.last_motion_at = 0.0
        self.previous_gray = None
        self.model = None
        self.detections = []
        self.detection_lock = threading.Lock()
        self.detection_error = None
        self.frame_number = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self._load_detector()
        self.worker = threading.Thread(target=self._capture_loop, daemon=True)
        self.worker.start()

    def stop(self):
        self.running = False
        if self.capture:
            self.capture.release()
        with self.frame_condition:
            self.frame_condition.notify_all()

    def _register(self):
        payload = {
            "camera_id": CAMERA_ID,
            "name": CAMERA_NAME,
            "type": CAMERA_TYPE,
            "stream_url": EDGE_STREAM_URL,
            "source": CAMERA_SOURCE,
            "metadata": {"network": {"iot_segment": IOT_SEGMENT}},
            "vision_mode": VISION_MODE,
        }
        try:
            requests.post(f"{CORE_API_URL}/api/cameras", json=payload, timeout=3)
        except requests.RequestException:
            pass

    def _load_detector(self):
        if not DETECTION_ENABLED:
            return
        if YOLO is None:
            self.detection_error = "ultralytics is not installed"
            return
        try:
            self.model = YOLO(DETECTION_MODEL)
        except Exception as exc:
            self.detection_error = str(exc)
            self.model = None

    def _heartbeat(self):
        try:
            requests.post(
                f"{CORE_API_URL}/api/cameras/{CAMERA_ID}/heartbeat",
                json={"fps": round(self.fps, 2), "status": self.status},
                timeout=3,
            )
        except requests.RequestException:
            pass

    def _motion_event(self):
        try:
            requests.post(
                f"{CORE_API_URL}/api/events",
                json={
                    "camera_id": CAMERA_ID,
                    "type": "motion",
                    "description": "Motion detected by ARGUS Edge",
                    "metadata": {"source": "opencv"},
                },
                timeout=3,
            )
        except requests.RequestException:
            pass

    def _detection_event(self, detection):
        try:
            requests.post(
                f"{CORE_API_URL}/api/events",
                json={
                    "camera_id": CAMERA_ID,
                    "type": "object_detected",
                    "confidence": detection["confidence"],
                    "object_name": detection["label"],
                    "description": (
                        f"{detection['label']} tracked as #{detection['track_id']}"
                    ),
                    "metadata": {
                        "source": "ultralytics",
                        "track_id": detection["track_id"],
                        "bbox": detection["bbox"],
                        "vision_mode": VISION_MODE,
                    },
                },
                timeout=3,
            )
        except requests.RequestException:
            pass

    def _run_detection(self, frame):
        if self.model is None or self.frame_number % DETECTION_INTERVAL:
            return
        try:
            results = self.model.track(
                frame,
                persist=True,
                conf=DETECTION_CONFIDENCE,
                classes=list(DETECTION_CLASSES) or None,
                verbose=False,
            )
            current = []
            for result in results:
                boxes = result.boxes
                names = result.names
                for index in range(len(boxes)):
                    coordinates = boxes.xyxy[index].cpu().tolist()
                    confidence = float(boxes.conf[index].cpu().item())
                    class_id = int(boxes.cls[index].cpu().item())
                    track_id = (
                        int(boxes.id[index].cpu().item())
                        if boxes.id is not None
                        else None
                    )
                    current.append(
                        {
                            "label": names[class_id],
                            "confidence": round(confidence, 4),
                            "track_id": track_id,
                            "bbox": [round(value) for value in coordinates],
                        }
                    )
            with self.detection_lock:
                previous_keys = {
                    (item["label"], item["track_id"]) for item in self.detections
                }
                self.detections = current
            for detection in current:
                key = (detection["label"], detection["track_id"])
                if key not in previous_keys:
                    threading.Thread(
                        target=self._detection_event,
                        args=(detection,),
                        daemon=True,
                    ).start()
        except Exception as exc:
            self.detection_error = str(exc)

    def _draw_detections(self, frame):
        with self.detection_lock:
            detections = list(self.detections)
        for detection in detections:
            x1, y1, x2, y2 = detection["bbox"]
            label = f"{detection['label']} {detection['confidence']:.0%}"
            if detection["track_id"] is not None:
                label += f"  #{detection['track_id']}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 255), 2)
            text_size, baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2
            )
            top = max(y1 - text_size[1] - baseline - 6, 0)
            cv2.rectangle(
                frame,
                (x1, top),
                (x1 + text_size[0] + 8, y1),
                (0, 220, 255),
                -1,
            )
            cv2.putText(
                frame,
                label,
                (x1 + 4, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (10, 10, 10),
                2,
                cv2.LINE_AA,
            )

    def _capture_loop(self):
        self._register()
        last_heartbeat = 0.0
        frames = 0
        fps_started = time.monotonic()

        while self.running:
            if self.capture is None or not self.capture.isOpened():
                self.status = "degraded"
                self.capture = cv2.VideoCapture(camera_source())
                if not self.capture.isOpened():
                    self.status = "offline"
                    self._heartbeat()
                    time.sleep(2)
                    continue

            ok, frame = self.capture.read()
            if not ok:
                self.status = "degraded"
                self.capture.release()
                self.capture = None
                time.sleep(1)
                continue

            frames += 1
            self.frame_number += 1
            elapsed = time.monotonic() - fps_started
            if elapsed >= 1:
                self.fps = frames / elapsed
                frames = 0
                fps_started = time.monotonic()

            self.status = "online"
            if MOTION_ENABLED:
                self._detect_motion(frame)

            self._run_detection(frame)
            self._draw_detections(frame)

            ok, encoded = cv2.imencode(".jpg", frame)
            if ok:
                with self.frame_condition:
                    self.last_frame = encoded.tobytes()
                    self.frame_condition.notify_all()

            if time.monotonic() - last_heartbeat >= 5:
                self._heartbeat()
                last_heartbeat = time.monotonic()

    def _detect_motion(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (320, 180))
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        if self.previous_gray is not None:
            difference = cv2.absdiff(self.previous_gray, gray)
            score = float(difference.mean())
            now = time.monotonic()
            if (
                score >= MOTION_THRESHOLD
                and now - self.last_motion_at >= MOTION_COOLDOWN_SECONDS
            ):
                self.last_motion_at = now
                threading.Thread(target=self._motion_event, daemon=True).start()
        self.previous_gray = gray

    def stream(self) -> Generator[bytes, None, None]:
        while self.running:
            with self.frame_condition:
                if self.last_frame is None:
                    self.frame_condition.wait(timeout=1)
                frame = self.last_frame
            if frame:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"


app = FastAPI(title="ARGUS Edge Camera", version="0.1.0")
agent = CameraAgent()


@app.on_event("startup")
def startup():
    agent.start()


@app.on_event("shutdown")
def shutdown():
    agent.stop()


@app.get("/health")
def health():
    return {
        "camera_id": CAMERA_ID,
        "status": agent.status,
        "fps": round(agent.fps, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vision_mode": VISION_MODE,
        "detection_enabled": DETECTION_ENABLED,
        "detector": DETECTION_MODEL if agent.model else None,
        "detection_error": agent.detection_error,
        "detections": len(agent.detections),
    }


@app.get("/discover")
def discover(max_index: int = 5):
    """Discover available local camera indexes on the Edge host."""
    max_index = max(1, min(max_index, 10))
    cameras = []
    for index in range(max_index):
        capture = cv2.VideoCapture(index)
        available = capture.isOpened()
        if available:
            ok, frame = capture.read()
            cameras.append(
                {
                    "source": str(index),
                    "available": bool(ok),
                    "width": int(frame.shape[1]) if ok else None,
                    "height": int(frame.shape[0]) if ok else None,
                }
            )
        capture.release()
    return {"cameras": cameras, "max_index": max_index}


@app.get("/config")
def config():
    return {
        "camera_id": CAMERA_ID,
        "camera_name": CAMERA_NAME,
        "camera_type": CAMERA_TYPE,
        "camera_source": CAMERA_SOURCE,
        "core_api_url": CORE_API_URL,
        "stream_url": EDGE_STREAM_URL,
        "iot_segment": IOT_SEGMENT,
        "vision_mode": VISION_MODE,
        "detection_enabled": DETECTION_ENABLED,
        "detection_model": DETECTION_MODEL,
    }


@app.get("/stream")
def stream():
    return StreamingResponse(
        agent.stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
