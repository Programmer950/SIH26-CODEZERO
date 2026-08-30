import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from Vehicle_tracking_engine import TrafficTrackingEngine

class TestSpeedTelemetry(unittest.TestCase):
    def setUp(self):
        self.engine = TrafficTrackingEngine(db_config={})

    @patch.object(TrafficTrackingEngine, 'get_db_connection')
    def test_reconstruct_trajectory_empty(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = False
        mock_cur.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value = mock_conn

        res = self.engine.reconstruct_trajectory("TN09AB1234")
        self.assertEqual(res["type"], "FeatureCollection")
        self.assertEqual(res["properties"]["total_sightings"], 0)
        self.assertEqual(res["properties"]["total_trip_avg_speed_kmh"], 0.0)
        self.assertEqual(res["total_trip_avg_speed_kmh"], 0.0)
        self.assertEqual(len(res["features"]), 0)

    @patch.object(TrafficTrackingEngine, 'get_db_connection')
    @patch.object(TrafficTrackingEngine, 'get_markov_predictions')
    def test_reconstruct_trajectory_single_node(self, mock_markov, mock_get_conn):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = False
        mock_cur.fetchall.return_value = [
            {
                "event_id": 1,
                "camera_id": "CAM_01",
                "camera_name": "Camera 1",
                "lat": 13.0827,
                "lon": 80.2707,
                "plate_text": "TN09AB1234",
                "ocr_confidence": 0.95,
                "vehicle_class": "SUV",
                "vehicle_color": "White",
                "plate_crop_url": None,
                "event_time": datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc),
                "timestamp": "2026-08-27T10:00:00Z",
                "distance_from_prev_km": 0.0
            }
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        mock_markov.return_value = []

        res = self.engine.reconstruct_trajectory("TN09AB1234")
        self.assertEqual(res["properties"]["total_sightings"], 1)
        self.assertEqual(res["properties"]["total_distance_km"], 0.0)
        self.assertEqual(res["properties"]["total_trip_avg_speed_kmh"], 0.0)
        self.assertEqual(res["total_trip_avg_speed_kmh"], 0.0)
        
        point_features = [f for f in res["features"] if f["geometry"]["type"] == "Point"]
        self.assertEqual(len(point_features), 1)
        self.assertEqual(point_features[0]["properties"]["distance_from_prev_km"], 0.0)
        self.assertEqual(point_features[0]["properties"]["segment_speed_kmh"], 0.0)

    @patch.object(TrafficTrackingEngine, 'get_db_connection')
    @patch.object(TrafficTrackingEngine, 'get_markov_predictions')
    def test_reconstruct_trajectory_multi_node_normal_speed(self, mock_markov, mock_get_conn):
        t0 = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 8, 27, 10, 15, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 27, 10, 30, 0, tzinfo=timezone.utc)

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = False
        mock_cur.fetchall.return_value = [
            {
                "event_id": 1,
                "camera_id": "CAM_01",
                "camera_name": "Camera 1",
                "lat": 13.0827,
                "lon": 80.2707,
                "speed_limit_kmh": 40,
                "plate_text": "TN09AB1234",
                "ocr_confidence": 0.95,
                "vehicle_class": "SUV",
                "vehicle_color": "White",
                "plate_crop_url": None,
                "event_time": t0,
                "timestamp": t0.isoformat(),
                "distance_from_prev_km": 0.0
            },
            {
                "event_id": 2,
                "camera_id": "CAM_02",
                "camera_name": "Camera 2",
                "lat": 13.0722,
                "lon": 80.2678,
                "speed_limit_kmh": 50,
                "plate_text": "TN09AB1234",
                "ocr_confidence": 0.92,
                "vehicle_class": "SUV",
                "vehicle_color": "White",
                "plate_crop_url": None,
                "event_time": t1,
                "timestamp": t1.isoformat(),
                "distance_from_prev_km": 2.5
            },
            {
                "event_id": 3,
                "camera_id": "CAM_03",
                "camera_name": "Camera 3",
                "lat": 13.0645,
                "lon": 80.2642,
                "speed_limit_kmh": 60,
                "plate_text": "TN09AB1234",
                "ocr_confidence": 0.90,
                "vehicle_class": "SUV",
                "vehicle_color": "White",
                "plate_crop_url": None,
                "event_time": t2,
                "timestamp": t2.isoformat(),
                "distance_from_prev_km": 3.0
            }
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        mock_markov.return_value = []

        res = self.engine.reconstruct_trajectory("TN09AB1234")
        self.assertEqual(res["properties"]["total_sightings"], 3)
        self.assertEqual(res["properties"]["total_distance_km"], 5.5)

        points = [f for f in res["features"] if f["geometry"]["type"] == "Point"]
        self.assertEqual(len(points), 3)
        self.assertEqual(points[0]["properties"]["segment_speed_kmh"], 0.0)
        # Point 1: 50 km/h road, SUV -> predictable speed ~40-50 km/h
        self.assertTrue(30.0 <= points[1]["properties"]["segment_speed_kmh"] <= 55.0)
        # Point 2: 60 km/h road, SUV -> predictable speed ~45-60 km/h
        self.assertTrue(35.0 <= points[2]["properties"]["segment_speed_kmh"] <= 65.0)
        # Average speed should be realistic city speed
        self.assertTrue(30.0 <= res["properties"]["total_trip_avg_speed_kmh"] <= 60.0)

    @patch.object(TrafficTrackingEngine, 'get_db_connection')
    @patch.object(TrafficTrackingEngine, 'get_markov_predictions')
    def test_reconstruct_trajectory_unreliable_time_resilience(self, mock_markov, mock_get_conn):
        t0 = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)
        # Duplicate timestamp -> dt = 0
        t1 = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)
        # 1-second timestamp difference for 2 km
        t2 = datetime(2026, 8, 27, 10, 0, 1, tzinfo=timezone.utc)

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = False
        mock_cur.fetchall.return_value = [
            {
                "event_id": 1,
                "camera_id": "CAM_01",
                "lat": 13.0827,
                "lon": 80.2707,
                "speed_limit_kmh": 40,
                "vehicle_class": "Auto-Rickshaw",
                "plate_text": "TN09AB1234",
                "ocr_confidence": 0.95,
                "event_time": t0,
                "timestamp": t0.isoformat(),
                "distance_from_prev_km": 0.0
            },
            {
                "event_id": 2,
                "camera_id": "CAM_02",
                "lat": 13.0722,
                "lon": 80.2678,
                "speed_limit_kmh": 40,
                "vehicle_class": "Auto-Rickshaw",
                "plate_text": "TN09AB1234",
                "ocr_confidence": 0.92,
                "event_time": t1,
                "timestamp": t1.isoformat(),
                "distance_from_prev_km": 1.2
            },
            {
                "event_id": 3,
                "camera_id": "CAM_03",
                "lat": 13.0645,
                "lon": 80.2642,
                "speed_limit_kmh": 80,
                "vehicle_class": "Sedan",
                "plate_text": "TN09AB1234",
                "ocr_confidence": 0.90,
                "event_time": t2,
                "timestamp": t2.isoformat(),
                "distance_from_prev_km": 3.0
            }
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        mock_markov.return_value = []

        res = self.engine.reconstruct_trajectory("TN09AB1234")
        points = [f for f in res["features"] if f["geometry"]["type"] == "Point"]
        # Node 1: initial 0
        self.assertEqual(points[0]["properties"]["segment_speed_kmh"], 0.0)
        # Node 2: Auto-Rickshaw on 40 km/h road -> realistic speed ~22-35 km/h, NEVER 0 or 180
        self.assertTrue(20.0 <= points[1]["properties"]["segment_speed_kmh"] <= 35.0)
        # Node 3: Sedan on 80 km/h expressway -> realistic speed ~55-75 km/h, NEVER 180
        self.assertTrue(50.0 <= points[2]["properties"]["segment_speed_kmh"] <= 75.0)
        # Trip avg speed should be realistic ~30-65 km/h
        self.assertTrue(25.0 <= res["properties"]["total_trip_avg_speed_kmh"] <= 70.0)

    @patch.object(TrafficTrackingEngine, 'get_db_connection')
    def test_get_all_vehicles(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            {
                "plate_text": "TN09AB1234",
                "vehicle_class": "SUV",
                "vehicle_color": "White",
                "total_sightings": 6,
                "first_seen": "2026-08-27 10:00:00+00",
                "last_seen": "2026-08-27 10:45:00+00",
                "last_camera_id": "CAM_AN_06",
                "last_camera_name": "Teynampet Signal",
                "avg_confidence": 0.94,
                "is_watchlist": True,
                "watchlist_reason": "Stolen Vehicle",
                "watchlist_priority": "CRITICAL"
            }
        ]
        mock_cur.fetchone.return_value = {"count": 1}
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value = mock_conn

        res = self.engine.get_all_vehicles()
        self.assertEqual(res["total_vehicles"], 1)
        self.assertEqual(len(res["vehicles"]), 1)
        self.assertEqual(res["vehicles"][0]["plate_text"], "TN09AB1234")
        self.assertTrue(res["vehicles"][0]["is_watchlist"])

if __name__ == "__main__":
    unittest.main()
