import json
from datetime import datetime, timezone
from Vehicle_tracking_engine import TrafficTrackingEngine

# Database connection credentials
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "SIH26",
    "user": "postgres",
    "password": "root"
}


def verify_geojson_engine():
    print("=" * 65)
    print("🚦 TESTING GEOJSON TRAJECTORY ENGINE (SIH26)")
    print("=" * 65)

    engine = TrafficTrackingEngine(db_config=DB_CONFIG)

    # 1. Ensure test cameras exist in the database
    conn = engine.get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
                    INSERT INTO cameras (camera_id, name, latitude, longitude, speed_limit_kmh)
                    VALUES ('CAM_01_KOYAMBEDU', 'Koyambedu Roundabout', 13.0732, 80.1937, 50),
                           ('CAM_02_ANNA_NAGAR', 'Anna Nagar Roundtana', 13.0850, 80.2101, 50),
                           ('CAM_03_T_NAGAR', 'Panagal Park T Nagar', 13.0418, 80.2341, 40) ON CONFLICT (camera_id) DO
                    UPDATE
                        SET name = EXCLUDED.name, latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude;
                    """)
        conn.commit()
    conn.close()

    # 2. Ingest Multi-Camera Sightings for Target Vehicle (including OCR glare typo 'B' -> '8')
    print("\n[Step 1] Ingesting Vehicle Sightings...")

    # Sighting 1: Cam 1 (Clean OCR)
    s1 = engine.ingest_detection({
        "camera_id": "CAM_01_KOYAMBEDU",
        "plate_text": "TN09AB1234",
        "ocr_confidence": 0.96,
        "timestamp": "2026-08-27T10:00:00Z",
        "vehicle_class": "SUV",
        "vehicle_color": "White",
        "embedding": [0.85, 0.12, 0.44],
        "plate_crop_url": "/static/crops/evt_1.jpg"
    })
    print(f" -> Cam 1 Recorded: TN09AB1234 (Event ID: {s1['event_id']})")

    # Sighting 2: Cam 2 (OCR Glare Typo: B -> 8)
    s2 = engine.ingest_detection({
        "camera_id": "CAM_02_ANNA_NAGAR",
        "plate_text": "TN09A81234",
        "ocr_confidence": 0.88,
        "timestamp": "2026-08-27T10:14:00Z",
        "vehicle_class": "SUV",
        "vehicle_color": "White",
        "embedding": [0.83, 0.10, 0.46],
        "plate_crop_url": "/static/crops/evt_2.jpg"
    })
    print(f" -> Cam 2 Recorded: TN09A81234 [Typo] (Event ID: {s2['event_id']})")

    # Sighting 3: Cam 3 (Clean OCR)
    s3 = engine.ingest_detection({
        "camera_id": "CAM_03_T_NAGAR",
        "plate_text": "TN09AB1234",
        "ocr_confidence": 0.94,
        "timestamp": "2026-08-27T10:28:00Z",
        "vehicle_class": "SUV",
        "vehicle_color": "White",
        "embedding": [0.84, 0.11, 0.45],
        "plate_crop_url": "/static/crops/evt_3.jpg"
    })
    print(f" -> Cam 3 Recorded: TN09AB1234 (Event ID: {s3['event_id']})")

    # 3. Query Trajectory and Receive GeoJSON
    print("\n[Step 2] Querying Reconstructed Trajectory for 'TN09AB1234'...")
    geojson_result = engine.reconstruct_trajectory(
        target_plate="TN09AB1234",
        start_time="2026-08-27T09:00:00Z",
        end_time="2026-08-27T12:00:00Z"
    )

    # 4. GeoJSON Structural Verification
    print("\n[Step 3] Validating GeoJSON Schema Compliance:")
    assert geojson_result.get("type") == "FeatureCollection", "❌ Root must be 'FeatureCollection'"
    assert "features" in geojson_result, "❌ 'features' array missing"

    features = geojson_result["features"]
    total_features = len(features)
    print(f" ✅ Root Type: {geojson_result['type']}")
    print(f" ✅ Total Features Generated: {total_features}")
    print(f" ✅ Total Sightings Resolved: {geojson_result['properties']['total_sightings']}")

    # Check LineString
    linestring_features = [f for f in features if f["geometry"]["type"] == "LineString"]
    point_features = [f for f in features if f["geometry"]["type"] == "Point"]

    assert len(linestring_features) == 1, "❌ LineString route feature missing"
    assert len(point_features) == 3, f"❌ Expected 3 Point sightings, got {len(point_features)}"

    print(f" ✅ Route Geometry: LineString with {len(linestring_features[0]['geometry']['coordinates'])} waypoints")
    print(f" ✅ Map Pins: {len(point_features)} Point features")

    # 5. Coordinate Format Check ([lon, lat])
    for pt in point_features:
        coords = pt["geometry"]["coordinates"]
        # In India, Lon is ~80 and Lat is ~13
        assert coords[0] > 70 and coords[1] < 20, f"❌ Invalid [lon, lat] ordering: {coords}"
    print(" ✅ Coordinate Order: Standard GeoJSON [Longitude, Latitude] confirmed")

    # 6. Pretty Print JSON Output
    print("\n[Step 4] Serialized GeoJSON Output Payload:")
    print("-" * 65)
    print(json.dumps(geojson_result, indent=2))
    print("-" * 65)
    print("🎉 ALL CHECKS PASSED. Ready for Mapbox/Leaflet consumption.")


if __name__ == "__main__":
    verify_geojson_engine()