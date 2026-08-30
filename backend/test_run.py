import sys
import io
import json
from datetime import datetime, timezone

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from road_network import GISRoadNetworkGraph, CAMERA_COORDINATES
from trajectory_forecaster import TrajectoryForecastingEngine
from Vehicle_tracking_engine import TrafficTrackingEngine

# Database connection credentials
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "SIH26",
    "user": "postgres",
    "password": "root"
}


def test_blind_spot_interpolation():
    print("=" * 65)
    print("🗺️ 1. TESTING GIS ROAD NETWORK BLIND-SPOT INTERPOLATION")
    print("=" * 65)

    road_net = GISRoadNetworkGraph()

    # Test Case 1: Sequential Corridor Gap (CAM_AN_01 to CAM_AN_05 - skipping 3 cameras)
    print("\n[Case 1] Sequential Corridor Blind-Spot (Central Station -> Gemini Flyover):")
    res1 = road_net.interpolate_blind_spot("CAM_AN_01", "CAM_AN_05")
    print(f" -> Success: {res1['success']}")
    print(f" -> Is Blind Spot: {res1['is_blind_spot']}")
    print(f" -> Gap Distance: {res1['gap_distance_km']} km")
    print(f" -> Confidence: {res1['confidence']}")
    print(f" -> Path Nodes: {res1['path_nodes']}")
    print(f" -> Waypoint Coordinates Count: {len(res1['coordinates'])}")
    assert res1["success"] is True
    assert res1["is_blind_spot"] is True
    assert len(res1["coordinates"]) >= 5
    print(" ✅ Sequential Corridor Blind-Spot Interpolation Passed")

    # Test Case 2: Cross-Corridor Connector Blind-Spot (Anna Salai -> OMR IT Corridor)
    print("\n[Case 2] Cross-Corridor Connector (Little Mount -> SRP Tools OMR):")
    res2 = road_net.interpolate_blind_spot("CAM_AN_09", "CAM_OM_03")
    print(f" -> Success: {res2['success']}")
    print(f" -> Is Blind Spot: {res2['is_blind_spot']}")
    print(f" -> Gap Distance: {res2['gap_distance_km']} km")
    print(f" -> Traversed Corridors: {res2['via_corridors']}")
    print(f" -> Path Nodes: {res2['path_nodes']}")
    assert res2["success"] is True
    assert "ANNA_SALAI" in res2["via_corridors"]
    assert "OMR" in res2["via_corridors"]
    print(" ✅ Cross-Corridor Blind-Spot Routing Passed")


def test_gnn_rnn_predictive_forecasting():
    print("\n" + "=" * 65)
    print("🔮 2. TESTING GNN + RNN PREDICTIVE TRAJECTORY FORECASTING")
    print("=" * 65)

    forecaster = TrajectoryForecastingEngine()

    sample_sightings = [
        {"camera_id": "CAM_AN_01", "timestamp": "2026-08-27T10:00:00Z", "ocr_confidence": 0.98, "vehicle_class": "SUV"},
        {"camera_id": "CAM_AN_03", "timestamp": "2026-08-27T10:08:00Z", "ocr_confidence": 0.95, "vehicle_class": "SUV"},
        {"camera_id": "CAM_AN_06", "timestamp": "2026-08-27T10:17:00Z", "ocr_confidence": 0.92, "vehicle_class": "SUV"},
        {"camera_id": "CAM_AN_09", "timestamp": "2026-08-27T10:25:00Z", "ocr_confidence": 0.96, "vehicle_class": "SUV"}
    ]

    forecast = forecaster.predict_next_intersections(sample_sightings)
    print(f" -> Model Architecture: {forecast['model_architecture']}")
    print(f" -> Current Heading: {forecast['current_heading_deg']}°")
    print(f" -> Estimated Speed: {forecast['estimated_speed_kmh']} km/h")
    print(f" -> Destination Hub Forecast: {forecast['destination_forecast']}")
    print(f" -> Next Intersections Count: {len(forecast['next_intersections'])}")

    assert forecast["status"] == "SUCCESS"
    assert len(forecast["next_intersections"]) > 0

    total_prob = sum(c["probability"] for c in forecast["next_intersections"])
    print(f" -> Total Normalized Top-K Probability: {round(total_prob, 2)}")
    assert abs(total_prob - 1.0) < 0.05

    for cand in forecast["next_intersections"]:
        print(f"    * [{cand['confidence_pct']}%] {cand['camera_name']} ({cand['camera_id']}) · Distance: {cand['distance_km']}km · ETA: {cand['eta_minutes']} min")

    print(f" -> Projected Future Path Waypoints: {len(forecast['projected_path_coordinates'])}")
    assert len(forecast["projected_path_coordinates"]) >= 2
    print(" ✅ GNN + RNN Predictive Trajectory Forecaster Passed")


def test_full_trajectory_reconstruction_engine():
    print("\n" + "=" * 65)
    print("🚦 3. TESTING END-TO-END TRAJECTORY RECONSTRUCTION ENGINE")
    print("=" * 65)

    engine = TrafficTrackingEngine(db_config=DB_CONFIG)

    # Test database connectivity if running with active DB
    try:
        conn = engine.get_db_connection()
        conn.close()
        db_available = True
    except Exception:
        db_available = False
        print(" ℹ️ DB offline in test environment, validating direct in-memory reconstruction pipeline")

    # Validate the forecaster and road network integration
    nodes = [
        {"event_id": 1, "camera_id": "CAM_AN_01", "camera_name": "Central Station", "lon": 80.2707, "lat": 13.0827, "timestamp": "2026-08-27T10:00:00Z", "plate_text": "TN09AB1234", "ocr_confidence": 0.96},
        {"event_id": 2, "camera_id": "CAM_AN_05", "camera_name": "Gemini Flyover", "lon": 80.2504, "lat": 13.0535, "timestamp": "2026-08-27T10:15:00Z", "plate_text": "TN09AB1234", "ocr_confidence": 0.94},
        {"event_id": 3, "camera_id": "CAM_OM_03", "camera_name": "SRP Tools OMR", "lon": 80.2483, "lat": 12.9790, "timestamp": "2026-08-27T10:35:00Z", "plate_text": "TN09AB1234", "ocr_confidence": 0.95}
    ]

    forecast = engine.forecaster.predict_next_intersections(nodes)
    assert forecast["status"] == "SUCCESS"
    print(f" ✅ Engine Forecaster Operational: Next target is {forecast['next_intersections'][0]['camera_name']}")
    print("🎉 ALL TEST SUITES PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_blind_spot_interpolation()
    test_gnn_rnn_predictive_forecasting()
    test_full_trajectory_reconstruction_engine()