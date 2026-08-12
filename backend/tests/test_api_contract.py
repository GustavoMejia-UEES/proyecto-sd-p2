import unittest
from unittest.mock import patch

from app.main import health, root
from app.schemas import CameraCreate, EventCreate


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


if __name__ == "__main__":
    unittest.main()
