import unittest
from unittest.mock import patch

from app.main import health, root
from app.schemas import (
    CameraCreate,
    CameraProvisionRequest,
    EventCreate,
    TaskCreate,
    TaskUpdate,
)


class ApiContractTests(unittest.TestCase):
    def test_root_identifies_argus(self):
        self.assertEqual(root()["system"], "ARGUS")
        self.assertEqual(root()["service"], "core-api")

    @patch("app.main.check_database", side_effect=ConnectionError)
    def test_health_reports_unavailable_database(self, _check_database):
        response = health()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.body, b'{"status":"degraded","database":"unavailable"}')

    def test_camera_and_event_payloads(self):
        camera = CameraCreate(camera_id="CAM-001", name="USB Camera")
        event = EventCreate(camera_id="CAM-001", type="motion")
        self.assertEqual(camera.camera_id, "CAM-001")
        self.assertEqual(event.type, "motion")

    def test_task_payload_matches_assignment_contract(self):
        task = TaskCreate(titulo="Estudiar Kubernetes")
        update = TaskUpdate(estado="Completada")
        self.assertEqual(task.estado, "Pendiente")
        self.assertEqual(update.estado, "Completada")

    def test_camera_task_payload_keeps_event_context(self):
        task = TaskCreate(
            titulo="Revisar alerta",
            source="camera",
            camera_id="CAM-001",
            event_id="EVT-001",
            priority="high",
        )
        self.assertEqual(task.source, "camera")
        self.assertEqual(task.camera_id, "CAM-001")
        self.assertEqual(task.priority, "high")

    def test_camera_provisioning_payload_keeps_network_target(self):
        config = CameraProvisionRequest(
            camera_id="CAM-001",
            name="Laptop",
            source="0",
            edge_host="100.64.0.10",
            edge_port=8081,
            iot_segment="iot-cameras",
        )
        self.assertEqual(config.edge_host, "100.64.0.10")
        self.assertEqual(config.iot_segment, "iot-cameras")

    def test_camera_modes_are_supported(self):
        for mode in ("motion", "cctv", "activity", "expression"):
            config = CameraProvisionRequest(
                camera_id="CAM-001", name="Laptop", vision_mode=mode
            )
            self.assertEqual(config.vision_mode, mode)


if __name__ == "__main__":
    unittest.main()
