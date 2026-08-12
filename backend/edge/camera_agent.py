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
CAPTURE_WIDTH = int(os.getenv("CAPTURE_WIDTH", "1280"))
CAPTURE_HEIGHT = int(os.getenv("CAPTURE_HEIGHT", "720"))
CAPTURE_FPS = int(os.getenv("CAPTURE_FPS", "30"))
CAPTURE_BUFFER_SIZE = max(1, int(os.getenv("CAPTURE_BUFFER_SIZE", "1")))
JPEG_QUALITY = max(40, min(95, int(os.getenv("JPEG_QUALITY", "82"))))
MOTION_ENABLED = env_bool("MOTION_ENABLED", True)
MOTION_THRESHOLD = float(os.getenv("MOTION_THRESHOLD", "18"))
MOTION_COOLDOWN_SECONDS = int(os.getenv("MOTION_COOLDOWN_SECONDS", "5"))
VISION_MODE = os.getenv("VISION_MODE", "motion").lower()
DETECTION_ENABLED = env_bool("DETECTION_ENABLED", VISION_MODE == "cctv")
EFFECTIVE_VISION_MODE = (
    "cctv" if DETECTION_ENABLED and VISION_MODE == "motion" else VISION_MODE
)
DETECTION_INTERVAL = max(1, int(os.getenv("DETECTION_INTERVAL", "3")))
DETECTION_CONFIDENCE = float(
    os.getenv("DETECTION_CONFIDENCE", "0.45").replace(",", ".")
)
DETECTION_MODEL = os.getenv("DETECTION_MODEL", "yolo11n.pt")
DETECTION_INPUT_SIZE = int(os.getenv("DETECTION_INPUT_SIZE", "640"))
DETECTION_DEVICE = os.getenv("DETECTION_DEVICE", "")
DETECTION_EVENT_COOLDOWN_SECONDS = float(
    os.getenv("DETECTION_EVENT_COOLDOWN_SECONDS", "8")
)
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
        self.detection_latency_ms = 0.0
        self.last_detection_at = None
        self.detection_event_times = {}
        self.last_event_at = None
        self.last_event_id = None
        self.last_event_error = None
        self.detection_condition = threading.Condition()
        self.pending_detection_frame = None
        self.detection_worker = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._load_detector()
        if self.model is not None:
            self.detection_worker = threading.Thread(
                target=self._detection_loop,
                daemon=True,
            )
            self.detection_worker.start()
        self.worker = threading.Thread(target=self._capture_loop, daemon=True)
        self.worker.start()

    def stop(self):
        self.running = False
        if self.capture:
            self.capture.release()
        with self.detection_condition:
            self.detection_condition.notify_all()
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
            "vision_mode": EFFECTIVE_VISION_MODE,
        }
        try:
            response = requests.post(
                f"{CORE_API_URL}/api/cameras", json=payload, timeout=3
            )
            if response.status_code == 409:
                requests.patch(
                    f"{CORE_API_URL}/api/cameras/{CAMERA_ID}",
                    json={
                        "name": CAMERA_NAME,
                        "type": CAMERA_TYPE,
                        "stream_url": EDGE_STREAM_URL,
                        "source": CAMERA_SOURCE,
                        "vision_mode": EFFECTIVE_VISION_MODE,
                        "metadata": {
                            "network": {"iot_segment": IOT_SEGMENT}
                        },
                    },
                    timeout=3,
                )
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
            response = requests.post(
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
                        "vision_mode": EFFECTIVE_VISION_MODE,
                    },
                },
                timeout=3,
            )
            if response.status_code == 201:
                event = response.json()
                self.last_event_at = datetime.now(timezone.utc).isoformat()
                self.last_event_id = event.get("id")
                self.last_event_error = None
            else:
                self.last_event_error = (
                    f"API returned HTTP {response.status_code}: {response.text[:200]}"
                )
        except requests.RequestException:
            self.last_event_error = "Could not reach core API"

    def _run_detection(self, frame):
        if self.model is None or self.frame_number % DETECTION_INTERVAL:
            return
        with self.detection_condition:
            self.pending_detection_frame = frame.copy()
            self.detection_condition.notify()

    def _detection_loop(self):
        while self.running:
            with self.detection_condition:
                while self.running and self.pending_detection_frame is None:
                    self.detection_condition.wait(timeout=0.5)
                if not self.running:
                    return
                frame = self.pending_detection_frame
                self.pending_detection_frame = None
            self._infer_detection(frame)

    def _infer_detection(self, frame):
        started = time.perf_counter()
        try:
            tracking_options = {
                "persist": True,
                "conf": DETECTION_CONFIDENCE,
                "classes": list(DETECTION_CLASSES) or None,
                "imgsz": DETECTION_INPUT_SIZE,
                "verbose": False,
            }
            if DETECTION_DEVICE:
                tracking_options["device"] = DETECTION_DEVICE
            results = self.model.track(frame, **tracking_options)
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
                self.detection_latency_ms = round(
                    (time.perf_counter() - started) * 1000, 2
                )
                self.last_detection_at = (
                    datetime.now(timezone.utc).isoformat() if current else None
                )
            for detection in current:
                key = (detection["label"], detection["track_id"])
                now = time.monotonic()
                last_event = self.detection_event_times.get(key, 0.0)
                if (
                    key not in previous_keys
                    or now - last_event >= DETECTION_EVENT_COOLDOWN_SECONDS
                ):
                    self.detection_event_times[key] = now
                    threading.Thread(
                        target=self._detection_event,
                        args=(detection,),
                        daemon=True,
                    ).start()
        except Exception as exc:
            self.detection_error = str(exc)
            self.detection_latency_ms = round(
                (time.perf_counter() - started) * 1000, 2
            )

    def _draw_hud(self, frame):
        with self.detection_lock:
            detection_count = len(self.detections)
        lines = [
            f"ARGUS // {CAMERA_ID}",
            f"MODE {EFFECTIVE_VISION_MODE.upper()}  |  FPS {self.fps:.1f}",
            f"TRACKED OBJECTS {detection_count}",
        ]
        if self.detection_latency_ms:
            lines.append(f"INFERENCE {self.detection_latency_ms:.0f}ms")
        overlay = frame.copy()
        height = 28 + (len(lines) * 23)
        cv2.rectangle(overlay, (0, 0), (280, height), (8, 14, 24), -1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)
        for index, line in enumerate(lines):
            color = (0, 220, 255) if index == 0 else (235, 240, 245)
            cv2.putText(
                frame,
                line,
                (12, 25 + index * 23),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52 if index else 0.62,
                color,
                1 if index else 2,
                cv2.LINE_AA,
            )

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
                self._configure_capture()
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
            self._draw_hud(frame)

            ok, encoded = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
            )
            if ok:
                with self.frame_condition:
                    self.last_frame = encoded.tobytes()
                    self.frame_condition.notify_all()

            if time.monotonic() - last_heartbeat >= 5:
                self._heartbeat()
                last_heartbeat = time.monotonic()

    def _configure_capture(self):
        if self.capture is None:
            return
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, CAPTURE_BUFFER_SIZE)
        if CAPTURE_WIDTH > 0:
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        if CAPTURE_HEIGHT > 0:
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
        if CAPTURE_FPS > 0:
            self.capture.set(cv2.CAP_PROP_FPS, CAPTURE_FPS)

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
        "vision_mode": EFFECTIVE_VISION_MODE,
        "requested_vision_mode": VISION_MODE,
        "detection_enabled": DETECTION_ENABLED,
        "detector": DETECTION_MODEL if agent.model else None,
        "detection_error": agent.detection_error,
        "detections": len(agent.detections),
        "detection_details": agent.detections,
        "labels": sorted({item["label"] for item in agent.detections}),
        "detection_latency_ms": agent.detection_latency_ms,
        "last_detection_at": agent.last_detection_at,
        "last_event_at": agent.last_event_at,
        "last_event_id": agent.last_event_id,
        "last_event_error": agent.last_event_error,
        "detection_interval": DETECTION_INTERVAL,
        "detection_input_size": DETECTION_INPUT_SIZE,
        "capture": {
            "target_width": CAPTURE_WIDTH,
            "target_height": CAPTURE_HEIGHT,
            "target_fps": CAPTURE_FPS,
            "jpeg_quality": JPEG_QUALITY,
        },
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
        "vision_mode": EFFECTIVE_VISION_MODE,
        "requested_vision_mode": VISION_MODE,
        "detection_enabled": DETECTION_ENABLED,
        "detection_model": DETECTION_MODEL,
        "detection_confidence": DETECTION_CONFIDENCE,
        "detection_interval": DETECTION_INTERVAL,
        "detection_input_size": DETECTION_INPUT_SIZE,
        "detection_device": DETECTION_DEVICE or "auto",
        "capture": {
            "width": CAPTURE_WIDTH,
            "height": CAPTURE_HEIGHT,
            "fps": CAPTURE_FPS,
            "buffer_size": CAPTURE_BUFFER_SIZE,
            "jpeg_quality": JPEG_QUALITY,
        },
    }


@app.get("/stream")
def stream():
    return StreamingResponse(
        agent.stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
