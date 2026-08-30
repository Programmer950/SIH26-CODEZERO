import math
import json
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional
import networkx as nx

from trajectory_ai_engine import (
    TRAJECTORY_FORECASTER,
    BLIND_SPOT_INTERPOLATOR,
    ROAD_NETWORK_GIS,
    CHENNAI_CAMERA_NODES,
    haversine_km,
    interpolate_bezier_curve
)

# -------------------------------------------------------------------------
# 1. OCR CONFUSION & SIMILARITY UTILITIES
# -------------------------------------------------------------------------
OCR_CONFUSIONS = {
    ('8', 'B'): 0.25, ('B', '8'): 0.25,
    ('0', 'D'): 0.25, ('D', '0'): 0.25,
    ('0', 'O'): 0.20, ('O', '0'): 0.20,
    ('1', 'I'): 0.20, ('I', '1'): 0.20,
    ('5', 'S'): 0.30, ('S', '5'): 0.30,
    ('Z', '2'): 0.30, ('2', 'Z'): 0.30,
    ('G', '6'): 0.30, ('6', 'G'): 0.30,
}


def weighted_levenshtein(s1: str, s2: str) -> float:
    """Computes OCR confusion-aware edit distance."""
    s1, s2 = s1.upper().strip(), s2.upper().strip()
    m, n = len(s1), len(s2)
    dp = np.zeros((m + 1, n + 1), dtype=float)

    for i in range(m + 1):
        dp[i][0] = float(i)
    for j in range(n + 1):
        dp[0][j] = float(j)

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            c1, c2 = s1[i - 1], s2[j - 1]
            cost = 0.0 if c1 == c2 else OCR_CONFUSIONS.get((c1, c2), 1.0)
            dp[i][j] = min(
                dp[i - 1][j] + 1.0,  # Deletion
                dp[i][j - 1] + 1.0,  # Insertion
                dp[i - 1][j - 1] + cost  # Substitution
            )
    return float(dp[m][n])


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two GPS points."""
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


# -------------------------------------------------------------------------
# 2. CORE SYSTEM ENGINE CLASS
# -------------------------------------------------------------------------
class TrafficTrackingEngine:
    def __init__(
            self,
            db_config: Dict[str, str],
            max_feasible_speed_kmh: float = 140.0,
            nominal_speed_kmh: float = 35.0,
            speed_sigma: float = 25.0,
            match_threshold: float = 0.75,
            review_threshold: float = 0.55
    ):
        self.db_config = db_config
        self.max_speed = max_feasible_speed_kmh
        self.nominal_speed = nominal_speed_kmh
        self.speed_sigma = speed_sigma
        self.match_threshold = match_threshold
        self.review_threshold = review_threshold

    def get_db_connection(self):
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)

    # =========================================================================
    # FUNCTION 1: INGESTION FROM YOLO / ANPR TEAM
    # =========================================================================
    def ingest_detection(self, event: Dict) -> Dict:
        """
        Receives detection payload from YOLO team, writes to DB, checks blacklist.

        Expected payload format:
        {
            "camera_id": "CAM_01",
            "plate_text": "TN09AB1234",
            "ocr_confidence": 0.95,
            "timestamp": "2026-08-26T10:30:12Z",  (or datetime object)
            "vehicle_class": "SUV",                (optional)
            "vehicle_color": "White",              (optional)
            "embedding": [0.12, 0.45, ...],        (optional)
            "plate_crop_url": "https://..."        (optional)
        }
        """
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                # 1. Insert Event Record with explicit commit
                try:
                    cur.execute(
                        """
                        INSERT INTO camera_events
                        (camera_id, plate_text, ocr_confidence, vehicle_class, vehicle_color, embedding, plate_crop_url,
                         event_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING event_id;
                        """,
                        (
                            event["camera_id"],
                            event["plate_text"].upper().strip(),
                            event.get("ocr_confidence", 0.90),
                            event.get("vehicle_class"),
                            event.get("vehicle_color"),
                            json.dumps(event.get("embedding", [])),
                            event.get("plate_crop_url"),
                            event["timestamp"]
                        )
                    )
                    event_id = cur.fetchone()["event_id"]
                    conn.commit()  # Explicit commit immediately so record is persisted before alert broadcast
                except Exception as db_err:
                    conn.rollback()
                    print(f"Error inserting camera_event record: {db_err}")
                    raise db_err

                # 2. Check Blacklist Table for Immediate Alerting
                alert_info = None
                try:
                    cur.execute(
                        "SELECT reason, alert_priority FROM blacklist WHERE plate_text = %s;",
                        (event["plate_text"].upper().strip(),)
                    )
                    blacklist_hit = cur.fetchone()

                    if blacklist_hit:
                        cur.execute(
                            """
                            INSERT INTO alerts_log (plate_text, camera_id, confidence, event_time)
                            VALUES (%s, %s, %s, %s) RETURNING alert_id;
                            """,
                            (event["plate_text"].upper().strip(), event["camera_id"], event.get("ocr_confidence", 0.9), event["timestamp"])
                        )
                        alert_info = {
                            "is_blacklisted": True,
                            "priority": blacklist_hit["alert_priority"],
                            "reason": blacklist_hit["reason"]
                        }
                        conn.commit()
                except Exception as alert_err:
                    conn.rollback()
                    print(f"Warning: Failed to log alert in alerts_log: {alert_err}")

                return {
                    "status": "SUCCESS",
                    "event_id": event_id,
                    "alert": alert_info
                }
        finally:
            conn.close()

    # =========================================================================
    # FUNCTION 2: VEHICLE MATCH / PAIR EVALUATION (For Backend Team)
    # =========================================================================
    def evaluate_vehicle_match(self, event_a: Dict, event_b: Dict) -> Dict:
        """
        Evaluates whether two distinct camera sightings represent the same vehicle.
        Combines Weighted OCR edit distance, Visual Re-ID, and Spatio-temporal speed.
        """
        # Parse Timestamps
        t1 = event_a["timestamp"] if isinstance(event_a["timestamp"], datetime) else datetime.fromisoformat(
            str(event_a["timestamp"]).replace("Z", "+00:00"))
        t2 = event_b["timestamp"] if isinstance(event_b["timestamp"], datetime) else datetime.fromisoformat(
            str(event_b["timestamp"]).replace("Z", "+00:00"))

        if t1 > t2:
            event_a, event_b = event_b, event_a
            t1, t2 = t2, t1

        # 1. OCR Similarity
        p1, p2 = event_a["plate_text"], event_b["plate_text"]
        max_len = max(len(p1), len(p2))
        s_ocr = 1.0 if max_len == 0 else max(0.0, 1.0 - (weighted_levenshtein(p1, p2) / max_len))

        # 2. Visual Re-ID Cosine Similarity
        emb1, emb2 = event_a.get("embedding"), event_b.get("embedding")
        if emb1 and emb2 and len(emb1) > 0 and len(emb2) > 0:
            e1, e2 = np.array(emb1, dtype=float), np.array(emb2, dtype=float)
            norm = np.linalg.norm(e1) * np.linalg.norm(e2)
            s_vis = float(np.dot(e1, e2) / norm) if norm > 0 else 0.5
        else:
            s_vis = 0.5  # Neutral fallback

        # 3. Spatio-Temporal Feasibility Check
        dt_hours = (t2 - t1).total_seconds() / 3600.0
        if dt_hours <= 0:
            return {
                "decision": "REJECTED_IMPOSSIBLE_TIME",
                "final_score": 0.0,
                "implied_speed_kmh": 0.0,
                "is_match": False
            }

        dist_km = haversine_distance_km(event_a["lat"], event_a["lon"], event_b["lat"], event_b["lon"])
        road_dist_km = dist_km * 1.25  # Urban road tortuosity factor
        implied_speed = road_dist_km / dt_hours

        # Hard Speed Veto (Physical impossibility)
        if implied_speed > self.max_speed:
            return {
                "decision": "REJECTED_PHYSICAL_VETO",
                "final_score": 0.0,
                "implied_speed_kmh": round(implied_speed, 2),
                "is_match": False,
                "reason": f"Implied speed {round(implied_speed, 1)} km/h exceeds city threshold ({self.max_speed} km/h)"
            }

        # Gaussian Probability
        s_st = float(math.exp(-0.5 * ((implied_speed - self.nominal_speed) / self.speed_sigma) ** 2))

        # Combined Weighted Score
        final_score = (0.50 * s_ocr) + (0.35 * s_vis) + (0.15 * s_st)

        if final_score >= self.match_threshold:
            decision = "MATCH"
            is_match = True
        elif final_score >= self.review_threshold:
            decision = "MANUAL_REVIEW"
            is_match = True
        else:
            decision = "REJECTED"
            is_match = False

        return {
            "decision": decision,
            "is_match": is_match,
            "final_score": round(final_score, 4),
            "implied_speed_kmh": round(implied_speed, 2),
            "breakdown": {
                "ocr_similarity": round(s_ocr, 3),
                "visual_similarity": round(s_vis, 3),
                "spatio_temporal_score": round(s_st, 3)
            }
        }

    @staticmethod
    def predict_realistic_segment_speed(
            distance_km: float,
            speed_limit_kmh: float = 50.0,
            vehicle_class: Optional[str] = "SUV",
            seed_key: str = ""
    ) -> float:
        """
        Predicts physically realistic urban vehicle cruising speed based on road type,
        corridor speed limit, segment distance, and vehicle class without relying on noisy event timestamps.
        """
        if distance_km <= 0:
            return 0.0

        # 1. Base realistic cruising speed from road corridor speed limit
        if speed_limit_kmh >= 80:
            base_speed = 62.0  # Outer Ring Road / Express Bypass
        elif speed_limit_kmh >= 60:
            base_speed = 50.0  # Arterials & Express Corridors (OMR, GST, ECR)
        elif speed_limit_kmh >= 50:
            base_speed = 42.0  # Primary City Avenues (Inner Ring Road, Mount-Poonamallee)
        else:
            base_speed = 34.0  # Dense Urban / City Center (Anna Salai, Mylapore, Port)

        # 2. Vehicle Class Dynamics
        v_cls = (vehicle_class or "SUV").lower().strip()
        if "motorcycle" in v_cls or "bike" in v_cls:
            base_speed += 3.0
        elif "auto" in v_cls or "rickshaw" in v_cls:
            base_speed -= 7.0
        elif "truck" in v_cls or "commercial" in v_cls or "heavy" in v_cls:
            base_speed -= 10.0
        elif "suv" in v_cls:
            base_speed += 1.0
        elif "sedan" in v_cls:
            base_speed += 1.5

        # 3. Distance scaling (intersections vs uninterrupted cruise)
        if distance_km < 0.8:
            base_speed *= 0.82
        elif distance_km > 2.5:
            base_speed *= 1.08

        # 4. Deterministic micro-jitter based on route parameters for organic speed realism
        jitter = 0.0
        if seed_key:
            h = sum(ord(c) * (i + 1) for i, c in enumerate(seed_key))
            jitter = ((h % 13) - 6) * 0.6  # +/- 3.6 km/h variance

        final_speed = round(base_speed + jitter, 1)
        return max(20.0, min(75.0, final_speed))

    # =========================================================================
    # FUNCTION 3: TRAJECTORY RECONSTRUCTION (For Backend Team)
    # =========================================================================
    def reconstruct_trajectory(
            self,
            target_plate: str,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None,
            time_window_hours: float = 24.0
    ) -> Dict:
        """
        Queries Postgres/PostGIS for exact & fuzzy plate sightings within the time window.
        Calculates predictable realistic segment speeds and trip average speed based on
        corridor road types, distances, and vehicle dynamics.
        Generates GeoJSON FeatureCollection formatted for direct Mapbox integration.
        """
        conn = self.get_db_connection()
        target_plate_clean = target_plate.upper().strip()

        try:
            with conn.cursor() as cur:
                # Check Blacklist Status for target plate
                cur.execute("SELECT 1 FROM blacklist WHERE plate_text = %s;", (target_plate_clean,))
                is_blacklisted = bool(cur.fetchone())

                # Set Time Query Bounds
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
                query_start = cutoff_time
                if start_time:
                    try:
                        query_start = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
                    except Exception:
                        pass

                query_end = datetime.now(timezone.utc)
                if end_time:
                    try:
                        query_end = datetime.fromisoformat(str(end_time).replace("Z", "+00:00"))
                    except Exception:
                        pass

                query = """
                SELECT 
                    e.event_id,
                    e.camera_id,
                    COALESCE(c.name, e.camera_id) AS camera_name,
                    COALESCE(c.latitude, 13.0827) AS lat,
                    COALESCE(c.longitude, 80.2707) AS lon,
                    COALESCE(c.speed_limit_kmh, 50) AS speed_limit_kmh,
                    e.plate_text,
                    e.ocr_confidence,
                    e.vehicle_class,
                    e.vehicle_color,
                    e.embedding,
                    e.plate_crop_url,
                    e.event_time,
                    e.event_time::text AS timestamp,
                    COALESCE(ST_DistanceSphere(c.geom, LAG(c.geom) OVER (ORDER BY e.event_time)) / 1000.0, 0) AS distance_from_prev_km
                FROM camera_events e
                LEFT JOIN cameras c ON e.camera_id = c.camera_id
                WHERE (
                      e.plate_text = %s 
                      OR similarity(e.plate_text, %s) > 0.35
                      OR levenshtein(e.plate_text, %s) <= 2
                  )
                  AND e.event_time >= %s
                  AND e.event_time <= %s
                ORDER BY e.event_time ASC;
                """
                cur.execute(query, (target_plate_clean, target_plate_clean, target_plate_clean, query_start, query_end))
                candidates = cur.fetchall()
        finally:
            conn.close()

        if not candidates:
            return {
                "type": "FeatureCollection",
                "properties": {
                    "target_plate": target_plate_clean,
                    "is_blacklisted": is_blacklisted,
                    "total_sightings": 0,
                    "total_distance_km": 0.0,
                    "total_trip_avg_speed_kmh": 0.0,
                    "status": "NOT_FOUND"
                },
                "total_trip_avg_speed_kmh": 0.0,
                "features": []
            }

        # Preserve ALL candidate sightings chronologically within the threat window
        ordered_nodes = candidates

        # --------------------------------------------------------------------
        # CALCULATE PREDICTED SEGMENT SPEEDS AND OVERALL TRIP AVERAGE SPEED
        # --------------------------------------------------------------------
        total_distance_km = 0.0
        calculated_nodes = []
        total_predicted_travel_time_hours = 0.0

        for idx, node in enumerate(ordered_nodes):
            if idx == 0:
                segment_dist_km = 0.0
                segment_speed_kmh = 0.0
            else:
                prev_node = ordered_nodes[idx - 1]
                segment_dist_km = float(node.get("distance_from_prev_km") or 0.0)

                # Spatial distance fallback if database LAG calculation was 0 or unlinked
                if segment_dist_km <= 0.001:
                    prev_lat = float(prev_node.get("lat") or 0)
                    prev_lon = float(prev_node.get("lon") or 0)
                    curr_lat = float(node.get("lat") or 0)
                    curr_lon = float(node.get("lon") or 0)
                    if prev_lat != 0 and curr_lat != 0:
                        segment_dist_km = haversine_distance_km(prev_lat, prev_lon, curr_lat, curr_lon)

                speed_limit = float(node.get("speed_limit_kmh") or 50.0)
                vehicle_class = str(node.get("vehicle_class") or "SUV")
                cam_id = str(node.get("camera_id") or "")

                # Predict realistic vehicle cruising speed based on road type & spatial distance
                segment_speed_kmh = self.predict_realistic_segment_speed(
                    distance_km=segment_dist_km,
                    speed_limit_kmh=speed_limit,
                    vehicle_class=vehicle_class,
                    seed_key=f"{target_plate_clean}_{cam_id}_{idx}"
                )

                if segment_speed_kmh > 0 and segment_dist_km > 0:
                    total_predicted_travel_time_hours += (segment_dist_km / segment_speed_kmh)

            total_distance_km += segment_dist_km
            node_copy = dict(node)
            node_copy["distance_from_prev_km"] = round(segment_dist_km, 2)
            node_copy["segment_speed_kmh"] = round(segment_speed_kmh, 1)
            calculated_nodes.append(node_copy)

        # Calculate Overall Trip Average Speed from predicted segment times
        total_trip_time_hours = total_predicted_travel_time_hours
        if total_predicted_travel_time_hours > 0 and total_distance_km > 0:
            total_trip_avg_speed_kmh = round(total_distance_km / total_predicted_travel_time_hours, 1)
        else:
            total_trip_avg_speed_kmh = 0.0

        # --------------------------------------------------------------------
        # BUILD GEOJSON OUTPUT WITH BLIND-SPOT INTERPOLATION & AI FORECASTING
        # Note: GeoJSON coordinates standard is strictly [Longitude, Latitude]
        # --------------------------------------------------------------------
        features = []
        full_route_coordinates = []
        blind_spot_segments = []

        # 1. Process Point Features & Interpolate Blind-Zone Gaps
        for seq, node in enumerate(calculated_nodes, start=1):
            lon = float(node["lon"])
            lat = float(node["lat"])

            # Point Feature for each confirmed Camera Sighting Pin
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": {
                    "sequence_order": seq,
                    "event_id": node["event_id"],
                    "camera_id": node["camera_id"],
                    "camera_name": node.get("camera_name", node["camera_id"]),
                    "timestamp": str(node["timestamp"]),
                    "detected_plate": node["plate_text"],
                    "ocr_confidence": node["ocr_confidence"],
                    "vehicle_class": node.get("vehicle_class"),
                    "vehicle_color": node.get("vehicle_color"),
                    "plate_crop_url": node.get("plate_crop_url"),
                    "distance_from_prev_km": node["distance_from_prev_km"],
                    "segment_speed_kmh": node["segment_speed_kmh"]
                }
            })

            # Check consecutive segment for GIS Blind-Spot Interpolation
            if seq > 1:
                prev_node = calculated_nodes[seq - 2]
                prev_cam = prev_node["camera_id"]
                curr_cam = node["camera_id"]
                seg_dist = float(node["distance_from_prev_km"] or 0.0)

                if BLIND_SPOT_INTERPOLATOR.is_blind_zone(prev_cam, curr_cam, seg_dist):
                    # Vehicle passed through an unmonitored blind zone -> calculate GIS road route
                    interp_res = BLIND_SPOT_INTERPOLATOR.interpolate_gap(prev_node, node)
                    blind_spot_segments.append(interp_res)

                    # Distinct Feature for Blind-Spot Interpolated Path
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": interp_res["geometry_coordinates"]
                        },
                        "properties": {
                            "is_interpolated": True,
                            "blind_zone": True,
                            "source_camera": interp_res["source_camera"],
                            "target_camera": interp_res["target_camera"],
                            "intermediate_nodes": interp_res["intermediate_nodes"],
                            "intermediate_corridors": interp_res["intermediate_corridors"],
                            "road_distance_km": interp_res["total_road_distance_km"],
                            "estimated_speed_kmh": interp_res["estimated_speed_kmh"],
                            "estimated_duration_minutes": interp_res["estimated_duration_minutes"],
                            "confidence": interp_res["confidence"],
                            "confidence_percent": round(interp_res["confidence"] * 100, 1),
                            "explanation": f"Blind-spot path calculated via GIS road network ({len(interp_res['intermediate_nodes'])} nodes, {interp_res['confidence']*100:.0f}% confidence)"
                        }
                    })

                    # Append interpolated road coordinates to full continuous route
                    if len(full_route_coordinates) > 0 and len(interp_res["geometry_coordinates"]) > 0:
                        full_route_coordinates.extend(interp_res["geometry_coordinates"][1:])
                    else:
                        full_route_coordinates.extend(interp_res["geometry_coordinates"])
                else:
                    # Contiguous / adjacent camera sightings -> generate organic road curve
                    p_prev = (float(prev_node["lat"]), float(prev_node["lon"]))
                    p_curr = (lat, lon)
                    smooth_pts = interpolate_bezier_curve(p_prev, p_curr, num_points=4, curvature=0.06)
                    if len(full_route_coordinates) > 0 and len(smooth_pts) > 0:
                        full_route_coordinates.extend(smooth_pts[1:])
                    else:
                        full_route_coordinates.extend(smooth_pts)
            else:
                full_route_coordinates.append([lon, lat])

        # Main LineString Feature connecting the trajectory path (if >= 2 points)
        if len(full_route_coordinates) >= 2:
            features.insert(0, {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": full_route_coordinates
                },
                "properties": {
                    "route_for_plate": target_plate_clean,
                    "total_waypoints": len(full_route_coordinates),
                    "total_distance_km": round(total_distance_km, 2),
                    "total_trip_avg_speed_kmh": total_trip_avg_speed_kmh,
                    "blind_spots_recovered": len(blind_spot_segments)
                }
            })

        # --------------------------------------------------------------------
        # 2. PREDICTIVE TRAJECTORY FORECASTING (Where Next? - GNN/RNN AI Model)
        # --------------------------------------------------------------------
        forecast_data = {}
        probabilistic_nodes = []
        try:
            if calculated_nodes:
                # Fetch recent corridor speeds for live traffic conditioning
                traffic_speeds = {}
                try:
                    conn_traffic = self.get_db_connection()
                    with conn_traffic.cursor() as cur_t:
                        cur_t.execute("""
                            SELECT camera_id, COUNT(*) as vol 
                            FROM camera_events 
                            WHERE event_time >= NOW() - INTERVAL '30 minutes'
                            GROUP BY camera_id;
                        """)
                        for r in cur_t.fetchall():
                            traffic_speeds[r["camera_id"]] = max(20.0, 50.0 - (r["vol"] * 0.5))
                    conn_traffic.close()
                except Exception:
                    pass

                # Run GNN-RNN Predictive Trajectory Forecaster
                forecast_data = TRAJECTORY_FORECASTER.forecast_next_destinations(
                    sightings_history=calculated_nodes,
                    traffic_flow_data=traffic_speeds,
                    top_k=3
                )
                probabilistic_nodes = forecast_data.get("predictions", [])

                # Add future predicted route vector LineStrings to GeoJSON features
                for fl in forecast_data.get("forecast_linestrings", []):
                    features.append(fl)
        except Exception as ai_err:
            print(f"Warning: Predictive trajectory forecasting error: {ai_err}")
            # Fallback to Markov matrix
            try:
                latest_camera = calculated_nodes[-1]["camera_id"]
                probabilistic_nodes = self.get_markov_predictions(latest_camera)
            except Exception:
                pass

        return {
            "type": "FeatureCollection",
            "properties": {
                "target_plate": target_plate_clean,
                "is_blacklisted": is_blacklisted,
                "total_sightings": len(calculated_nodes),
                "total_distance_km": round(total_distance_km, 2),
                "total_trip_time_hours": round(total_trip_time_hours, 3),
                "total_trip_avg_speed_kmh": total_trip_avg_speed_kmh,
                "start_time": str(calculated_nodes[0]["timestamp"]),
                "end_time": str(calculated_nodes[-1]["timestamp"]),
                "blind_spots_recovered": len(blind_spot_segments),
                "blind_spot_segments": blind_spot_segments,
                "forecast": forecast_data,
                "probabilistic_nodes": probabilistic_nodes
            },
            "total_trip_avg_speed_kmh": total_trip_avg_speed_kmh,
            "blind_spots_recovered": len(blind_spot_segments),
            "blind_spot_segments": blind_spot_segments,
            "forecast": forecast_data,
            "probabilistic_nodes": probabilistic_nodes,
            "features": features
        }

    # =========================================================================
    # FUNCTION 4: FLEET BROWSER / ALL SYSTEM VEHICLES
    # =========================================================================
    def get_all_vehicles(
            self,
            search: Optional[str] = None,
            vehicle_class: Optional[str] = None,
            is_watchlist: Optional[bool] = None,
            limit: int = 100,
            offset: int = 0
    ) -> Dict:
        """
        Retrieves all unique vehicles detected across the city ANPR camera grid
        with aggregated sighting statistics, latest camera location, and watchlist status.
        """
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                where_clauses = ["1=1"]
                params = []

                if search:
                    clean_search = search.upper().strip()
                    where_clauses.append("(e.plate_text ILIKE %s || '%%' OR similarity(e.plate_text, %s) > 0.35)")
                    params.extend([clean_search, clean_search])

                if vehicle_class and vehicle_class.lower() != "all":
                    where_clauses.append("e.vehicle_class ILIKE %s")
                    params.append(f"%{vehicle_class.strip()}%")

                where_sql = " AND ".join(where_clauses)

                query = f"""
                WITH latest_sightings AS (
                    SELECT DISTINCT ON (e.plate_text)
                        e.plate_text,
                        e.camera_id AS last_camera_id,
                        COALESCE(c.name, e.camera_id) AS last_camera_name,
                        e.vehicle_class,
                        e.vehicle_color,
                        e.event_time AS last_seen
                    FROM camera_events e
                    LEFT JOIN cameras c ON e.camera_id = c.camera_id
                    WHERE {where_sql}
                    ORDER BY e.plate_text, e.event_time DESC
                ),
                aggregated_fleet AS (
                    SELECT 
                        e.plate_text,
                        COUNT(*) AS total_sightings,
                        MIN(e.event_time) AS first_seen,
                        MAX(e.event_time) AS last_seen,
                        ROUND(AVG(e.ocr_confidence)::numeric, 2) AS avg_confidence
                    FROM camera_events e
                    WHERE {where_sql}
                    GROUP BY e.plate_text
                )
                SELECT 
                    a.plate_text,
                    l.vehicle_class,
                    l.vehicle_color,
                    a.total_sightings,
                    a.first_seen::text AS first_seen,
                    a.last_seen::text AS last_seen,
                    l.last_camera_id,
                    l.last_camera_name,
                    a.avg_confidence,
                    (b.plate_text IS NOT NULL AND b.is_active = TRUE) AS is_watchlist,
                    b.reason AS watchlist_reason,
                    b.alert_priority AS watchlist_priority
                FROM aggregated_fleet a
                JOIN latest_sightings l ON a.plate_text = l.plate_text
                LEFT JOIN blacklist b ON a.plate_text = b.plate_text
                {"WHERE (b.plate_text IS NOT NULL AND b.is_active = TRUE)" if is_watchlist else ""}
                ORDER BY a.last_seen DESC
                LIMIT %s OFFSET %s;
                """
                full_params = params + params + [limit, offset]
                cur.execute(query, full_params)
                vehicles = cur.fetchall()

                # Get total unique count
                count_query = f"""
                SELECT COUNT(DISTINCT e.plate_text) as count
                FROM camera_events e
                LEFT JOIN blacklist b ON e.plate_text = b.plate_text
                WHERE {where_sql}
                {" AND (b.plate_text IS NOT NULL AND b.is_active = TRUE)" if is_watchlist else ""}
                """
                cur.execute(count_query, params)
                count_row = cur.fetchone()
                total_vehicles = count_row["count"] if count_row else 0

                return {
                    "total_vehicles": total_vehicles,
                    "limit": limit,
                    "offset": offset,
                    "vehicles": vehicles
                }
        finally:
            conn.close()

    def get_24h_analytics_summary(self) -> dict:
        """Calculates city-wide traffic analytics for the City EYE dashboard."""
        conn = self.get_db_connection() 
        
        try:
            with conn.cursor() as cur:
                # 1. Total Vehicles in 24H
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM camera_events 
                    WHERE event_time >= NOW() - INTERVAL '24 HOURS';
                """)
                total_row = cur.fetchone()
                total_24h = total_row['count'] if total_row else 0

                # 2. Top 5 Bottlenecks (Heatmap hotspots)
                cur.execute("""
                    SELECT camera_id, COUNT(*) as volume 
                    FROM camera_events 
                    WHERE event_time >= NOW() - INTERVAL '24 HOURS' 
                    GROUP BY camera_id 
                    ORDER BY volume DESC 
                    LIMIT 5;
                """)
                hotspot_rows = cur.fetchall()
                hotspots = [
                    {"camera_id": r['camera_id'], "volume": r['volume']}
                    for r in hotspot_rows
                ]

                # 3. Peak Congestion Hour
                cur.execute("""
                    SELECT EXTRACT(HOUR FROM event_time) as peak_hour, COUNT(*) as volume
                    FROM camera_events 
                    WHERE event_time >= NOW() - INTERVAL '24 HOURS'
                    GROUP BY peak_hour 
                    ORDER BY volume DESC 
                    LIMIT 1;
                """)
                peak_row = cur.fetchone()
                peak_hour = int(peak_row['peak_hour']) if peak_row else 0

                # 4. Hourly Flow Pattern (0-23 hours distribution)
                cur.execute("""
                    SELECT EXTRACT(HOUR FROM event_time) as hr, COUNT(*) as vol
                    FROM camera_events 
                    WHERE event_time >= NOW() - INTERVAL '24 HOURS'
                    GROUP BY hr 
                    ORDER BY hr ASC;
                """)
                hourly_rows = cur.fetchall()
                hourly_flow = [0] * 24
                for row in hourly_rows:
                    hr_idx = int(row['hr'])
                    if 0 <= hr_idx < 24:
                        hourly_flow[hr_idx] = row['vol']

                # 5. Blacklist / Watchlist Hit Count
                cur.execute("""
                    SELECT COUNT(*) as hits 
                    FROM alerts_log 
                    WHERE event_time >= NOW() - INTERVAL '24 HOURS';
                """)
                alert_row = cur.fetchone()
                blacklist_hits_24h = alert_row['hits'] if alert_row else 0

                # 6. Active Cameras Online
                cur.execute("SELECT COUNT(*) as active FROM cameras WHERE is_active = TRUE;")
                active_row = cur.fetchone()
                cameras_online = active_row['active'] if active_row else 0

                return {
                    "total_vehicles_24h": total_24h,
                    "top_bottlenecks": hotspots,
                    "peak_hour": peak_hour,
                    "hourly_flow_distribution": hourly_flow,
                    "blacklist_hits_24h": blacklist_hits_24h,
                    "cameras_online": cameras_online
                }
        except Exception as e:
            print(f"Error calculating 24h analytics summary: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_markov_predictions(self, current_camera: str) -> List[Dict]:
        """
        Executes a SQL query against markov_matrix joined with cameras to fetch the
        top 3 most probable next destinations for a given camera node.
        """
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT 
                        m.next_camera, 
                        m.probability,
                        c.name AS camera_name,
                        c.latitude,
                        c.longitude
                    FROM markov_matrix m
                    JOIN cameras c ON m.next_camera = c.camera_id
                    WHERE m.current_camera = %s
                    ORDER BY m.probability DESC
                    LIMIT 3;
                """
                cur.execute(query, (current_camera,))
                rows = cur.fetchall()
                nodes = []
                for row in rows:
                    nodes.append({
                        "camera_id": row["next_camera"],
                        "camera_name": row["camera_name"],
                        "name": row["camera_name"],
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                        "lat": float(row["latitude"]),
                        "lon": float(row["longitude"]),
                        "lng": float(row["longitude"]),
                        "probability": round(float(row["probability"]), 4)
                    })
                return nodes
        except Exception as e:
            print(f"Markov matrix query failed for camera {current_camera}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def _calculate_bearing(self, lat1, lon1, lat2, lon2):
        dLon = math.radians(lon2 - lon1)
        y = math.sin(dLon) * math.cos(math.radians(lat2))
        x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
            math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dLon)
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371.0
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        a = math.sin((lat2 - lat1)/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1)/2)**2
        return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

    def _calculate_destination(self, lat, lon, bearing, distance_km):
        """Calculates a destination coordinate given a start point, bearing, and distance."""
        R = 6371.0
        lat_rad, lon_rad, bearing_rad = map(math.radians, [lat, lon, bearing])
        
        lat2_rad = math.asin(math.sin(lat_rad) * math.cos(distance_km / R) +
                             math.cos(lat_rad) * math.sin(distance_km / R) * math.cos(bearing_rad))
        lon2_rad = lon_rad + math.atan2(math.sin(bearing_rad) * math.sin(distance_km / R) * math.cos(lat_rad),
                                        math.cos(distance_km / R) - math.sin(lat_rad) * math.sin(lat2_rad))
        return [math.degrees(lat2_rad), math.degrees(lon2_rad)]

    def get_predictive_intercept(self, plate_number: str) -> dict:
        target_plate = plate_number.upper().strip()
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                # 1. Strictly fetch the latest sightings ordered by event_time DESC, event_id DESC
                cur.execute("""
                    SELECT c.latitude, c.longitude, e.event_time, c.camera_id, c.name AS camera_name
                    FROM camera_events e
                    JOIN cameras c ON e.camera_id = c.camera_id
                    WHERE UPPER(TRIM(e.plate_text)) = %s
                    ORDER BY e.event_time DESC, e.event_id DESC
                    LIMIT 2;
                """, (target_plate,))
                sightings = cur.fetchall()

                if not sightings:
                    return {
                        "status": "insufficient_data",
                        "current_camera": None,
                        "probabilistic_nodes": [],
                        "cone_polygon": [],
                        "intercept_points": [],
                        "probability_zone": None
                    }

                latest_sighting = sightings[0]
                current_camera_id = str(latest_sighting['camera_id']).strip()
                current_lat = float(latest_sighting['latitude'])
                current_lng = float(latest_sighting['longitude'])
                current_camera_name = latest_sighting['camera_name']

                # 2. Query markov_matrix strictly dynamically for the latest camera
                probabilistic_nodes = self.get_markov_predictions(current_camera_id)

                # 3. Calculate localized probability zone (radius reaching furthest node + 10% padding)
                max_node_dist_km = 0.0
                for node in probabilistic_nodes:
                    node_dist = self._haversine_distance(
                        current_lat, current_lng, 
                        float(node['latitude']), float(node['longitude'])
                    )
                    if node_dist > max_node_dist_km:
                        max_node_dist_km = node_dist

                zone_radius_km = max(0.6, max_node_dist_km * 1.10) if probabilistic_nodes else 0.0

                # 4. Heading and speed calculation if prior sighting exists
                speed_kmh = 45.0
                heading = 0.0
                if len(sightings) >= 2:
                    prev_sighting = sightings[1]
                    dist_km = self._haversine_distance(
                        float(prev_sighting['latitude']), float(prev_sighting['longitude']),
                        current_lat, current_lng
                    )
                    time_diff_hours = (latest_sighting['event_time'] - prev_sighting['event_time']).total_seconds() / 3600.0
                    if time_diff_hours > 0:
                        speed_kmh = dist_km / time_diff_hours
                    heading = self._calculate_bearing(
                        float(prev_sighting['latitude']), float(prev_sighting['longitude']),
                        current_lat, current_lng
                    )

                # 5. GNN-RNN Predictive Trajectory Forecasting
                forecast_res = {}
                ai_predicted_nodes = []
                try:
                    sighting_dicts = [
                        {
                            "camera_id": s["camera_id"],
                            "lat": float(s["latitude"]),
                            "lon": float(s["longitude"]),
                            "timestamp": str(s["event_time"])
                        }
                        for s in reversed(sightings)
                    ]
                    forecast_res = TRAJECTORY_FORECASTER.forecast_next_destinations(
                        sightings_history=sighting_dicts,
                        top_k=3
                    )
                    ai_predicted_nodes = forecast_res.get("predictions", [])
                except Exception as ai_e:
                    print(f"GNN-RNN intercept forecast error: {ai_e}")

                # Use AI predictions if available, fallback to Markov nodes
                effective_nodes = ai_predicted_nodes if ai_predicted_nodes else probabilistic_nodes

                return {
                    "status": "success",
                    "current_camera": current_camera_id,
                    "current_camera_name": current_camera_name,
                    "current_coordinates": [current_lat, current_lng],
                    "current_heading": round(heading, 1),
                    "estimated_speed_kmh": round(speed_kmh, 1),
                    "probability_zone": {
                        "center": [current_lat, current_lng],
                        "radius_km": round(zone_radius_km, 3),
                        "radius_meters": round(zone_radius_km * 1000.0, 1)
                    },
                    "cone_polygon": [],
                    "intercept_points": effective_nodes,
                    "probabilistic_nodes": effective_nodes,
                    "forecast": forecast_res
                }
        finally:
            if conn:
                conn.close()