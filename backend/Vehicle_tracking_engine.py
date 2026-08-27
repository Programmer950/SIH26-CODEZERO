import math
import json
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import networkx as nx

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
                # 1. Insert Event Record
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

                # 2. Check Blacklist Table for Immediate Alerting
                cur.execute(
                    "SELECT reason, alert_priority FROM blacklist WHERE plate_text = %s;",
                    (event["plate_text"].upper().strip(),)
                )
                blacklist_hit = cur.fetchone()

                alert_info = None
                if blacklist_hit:
                    cur.execute(
                        """
                        INSERT INTO alerts_log (plate_text, camera_id, confidence, event_time)
                        VALUES (%s, %s, %s, %s) RETURNING alert_id;
                        """,
                        (event["plate_text"], event["camera_id"], event.get("ocr_confidence", 0.9), event["timestamp"])
                    )
                    alert_info = {
                        "is_blacklisted": True,
                        "priority": blacklist_hit["alert_priority"],
                        "reason": blacklist_hit["reason"]
                    }

                conn.commit()
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

    # =========================================================================
    # FUNCTION 3: TRAJECTORY RECONSTRUCTION (For Backend Team)
    # =========================================================================
    def reconstruct_trajectory(self, target_plate: str, start_time: str, end_time: str) -> Dict:
        target_plate_clean = target_plate.upper().strip()
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                query = """
                SELECT 
                    e.event_id,
                    e.camera_id,
                    c.name AS camera_name,
                    c.latitude AS lat,
                    c.longitude AS lon,
                    e.plate_text,
                    e.ocr_confidence,
                    e.vehicle_class,
                    e.vehicle_color,
                    e.embedding,
                    e.plate_crop_url,
                    e.event_time::text AS timestamp
                FROM camera_events e
                JOIN cameras c ON e.camera_id = c.camera_id
                WHERE e.event_time >= %s::timestamptz 
                  AND e.event_time <= %s::timestamptz
                  AND (
                      e.plate_text = %s 
                      OR similarity(e.plate_text, %s) > 0.35
                      OR levenshtein(e.plate_text, %s) <= 2
                  )
                ORDER BY e.event_time ASC;
                """
                cur.execute(query, (start_time, end_time, target_plate_clean, target_plate_clean, target_plate_clean))
                candidates = cur.fetchall()
        finally:
            conn.close()

        if not candidates:
            return {
                "type": "FeatureCollection",
                "properties": {
                    "target_plate": target_plate_clean,
                    "total_sightings": 0,
                    "status": "NOT_FOUND"
                },
                "features": []
            }

        G = nx.DiGraph()
        for idx, item in enumerate(candidates):
            G.add_node(idx, **item)

        # 1. Connect chronological candidates if they pass fusion match
        for i in range(len(candidates)):
            # Look ahead to the next few candidates in time
            for j in range(i + 1, min(i + 4, len(candidates))):
                res = self.evaluate_vehicle_match(candidates[i], candidates[j])
                if res["is_match"]:
                    # Cost favors valid chronological transitions
                    G.add_edge(i, j, weight=1.0 - res["final_score"], metrics=res)

        # 2. Sequential Longest Valid Trajectory Chain (DAG traversal)
        # Find the longest path of valid transitions through time
        if G.number_of_edges() == 0:
            best_path = [0]
        else:
            # Find the path that visits the maximum number of verified nodes in sequence
            all_paths = []
            sources = [n for n, d in G.in_degree() if d == 0] or [0]
            targets = [n for n, d in G.out_degree() if d == 0] or [len(candidates) - 1]

            for s in sources:
                for t in targets:
                    if s != t and nx.has_path(G, s, t):
                        for p in nx.all_simple_paths(G, source=s, target=t):
                            all_paths.append(p)

            if all_paths:
                # Pick path that covers the most sightings (longest chain), break ties with highest confidence
                all_paths.sort(key=lambda p: len(p), reverse=True)
                best_path = all_paths[0]
            else:
                best_path = list(range(len(candidates)))

        ordered_nodes = [candidates[idx] for idx in best_path]

        # --------------------------------------------------------------------
        # BUILD GEOJSON OUTPUT
        # Note: GeoJSON coordinates standard is strictly [Longitude, Latitude]
        # --------------------------------------------------------------------
        features = []
        line_coordinates = []

        for seq, node in enumerate(ordered_nodes, start=1):
            lon = float(node["lon"])
            lat = float(node["lat"])
            line_coordinates.append([lon, lat])

            # Point Feature for each Camera Sighting Pin
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
                    "timestamp": node["timestamp"],
                    "detected_plate": node["plate_text"],
                    "ocr_confidence": node["ocr_confidence"],
                    "vehicle_class": node.get("vehicle_class"),
                    "vehicle_color": node.get("vehicle_color"),
                    "plate_crop_url": node.get("plate_crop_url")
                }
            })

        # LineString Feature connecting the trajectory path (if >= 2 points)
        if len(line_coordinates) >= 2:
            features.insert(0, {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": line_coordinates
                },
                "properties": {
                    "route_for_plate": target_plate_clean,
                    "total_waypoints": len(line_coordinates)
                }
            })

        return {
            "type": "FeatureCollection",
            "properties": {
                "target_plate": target_plate_clean,
                "total_sightings": len(ordered_nodes),
                "start_time": ordered_nodes[0]["timestamp"],
                "end_time": ordered_nodes[-1]["timestamp"]
            },
            "features": features
        }