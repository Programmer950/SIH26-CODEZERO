import os
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from Vehicle_tracking_engine import TrafficTrackingEngine

# ============================================================================
# 1. APPLICATION & ENGINE SETUP
# ============================================================================
app = FastAPI(
    title="City-Wide ANPR & Traffic Intelligence API",
    version="1.0.0",
    description="Backend API for edge ingestion, trajectory reconstruction, and traffic analytics."
)

# Enable CORS for Frontend (React/Mapbox)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust to ["http://localhost:3000", "http://localhost:5173"] in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database credentials
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "SIH26"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "root")
}

engine = TrafficTrackingEngine(db_config=DB_CONFIG)


# ============================================================================
# 2. WEBSOCKET CONNECTION MANAGER (FOR REAL-TIME BLACKLIST ALERTS)
# ============================================================================
class AlertConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_alert(self, alert_payload: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(alert_payload)
            except Exception:
                pass


alert_manager = AlertConnectionManager()


# ============================================================================
# 3. PYDANTIC SCHEMAS
# ============================================================================
class DetectionEventSchema(BaseModel):
    camera_id: str = Field(..., example="CAM_01_KOYAMBEDU")
    plate_text: str = Field(..., example="TN09AB1234")
    ocr_confidence: float = Field(0.90, ge=0.0, le=1.0)
    timestamp: str = Field(..., example="2026-08-26T10:30:12Z")
    vehicle_class: Optional[str] = Field("SUV", example="SUV")
    vehicle_color: Optional[str] = Field("White", example="White")
    embedding: Optional[List[float]] = Field(default=[], example=[0.142, -0.052, 0.811])
    plate_crop_url: Optional[str] = Field(None, example="https://cdn.cityanpr.org/crops/evt_1.jpg")


class PairwiseMatchSchema(BaseModel):
    event_a: Dict
    event_b: Dict

class CameraCreateSchema(BaseModel):
    camera_id: str = Field(..., example="CAM_06_VELACHERY")
    name: str = Field(..., example="Velachery Main Road Junction")
    latitude: float = Field(..., example=12.9750)
    longitude: float = Field(..., example=80.2200)
    direction_heading: Optional[int] = Field(90, ge=0, le=360)
    speed_limit_kmh: Optional[int] = Field(50, example=50)

class BlacklistCreateSchema(BaseModel):
    plate_text: str = Field(..., example="TN09XY5678")
    reason: str = Field(..., example="Stolen Vehicle FIR #2026/104")
    alert_priority: Optional[str] = Field("HIGH", example="HIGH")
    owner_name: Optional[str] = Field(None, example="Karthik S")
    vehicle_description: Optional[str] = Field(None, example="Grey Honda City")


# ============================================================================
# 4. REST API ROUTES
# ============================================================================

@app.get("/")
def health_check():
    return {"status": "ONLINE", "timestamp": datetime.now(timezone.utc).isoformat()}


# ----------------------------------------------------------------------------
# ROUTE 1: Edge Event Ingestion (Called by YOLO / Edge Workers)
# ----------------------------------------------------------------------------
@app.post("/api/v1/events", status_code=201)
async def ingest_event(event: DetectionEventSchema):
    try:
        result = engine.ingest_detection(event.dict())

        # If event triggered a blacklist match, broadcast immediately to connected UI clients
        if result.get("alert"):
            broadcast_payload = {
                "type": "BLACKLIST_ALERT",
                "camera_id": event.camera_id,
                "plate_text": event.plate_text,
                "timestamp": event.timestamp,
                "alert": result["alert"]
            }
            await alert_manager.broadcast_alert(broadcast_payload)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------------
# ROUTE 2: Trajectory Reconstruction (Called by Frontend Vehicle Search)
# ----------------------------------------------------------------------------
@app.get("/api/v1/vehicles/{plate}/trajectory")
def get_vehicle_trajectory(
        plate: str,
        start_time: Optional[str] = Query(None, example="2026-08-26T00:00:00Z"),
        end_time: Optional[str] = Query(None, example="2026-08-26T23:59:59Z")
):
    try:
        trajectory = engine.reconstruct_trajectory(
            target_plate=plate,
            start_time=start_time,
            end_time=end_time
        )
        return trajectory
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------------
# ROUTE 3: Pairwise Verification Inspector
# ----------------------------------------------------------------------------
@app.post("/api/v1/vehicles/match-check")
def check_vehicle_match(payload: PairwiseMatchSchema):
    try:
        return engine.evaluate_vehicle_match(payload.event_a, payload.event_b)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------------
# ROUTE 4: Macro Traffic Density & Heatmap
# ----------------------------------------------------------------------------
@app.get("/api/v1/analytics/heatmap")
def get_traffic_heatmap(minutes: int = 15):
    """
    Computes camera density and congestion index across all cameras over the last N minutes.
    """
    conn = engine.get_db_connection()
    try:
        with conn.cursor() as cur:
            query = """
                    SELECT c.camera_id, \
                           c.name, \
                           c.latitude, \
                           c.longitude, \
                           c.speed_limit_kmh, \
                           COUNT(e.event_id)                         AS vehicle_count, \
                           ROUND(COUNT(e.event_id)::numeric / %s, 2) AS vehicles_per_minute
                    FROM cameras c
                             LEFT JOIN camera_events e
                                       ON c.camera_id = e.camera_id
                                           AND e.event_time >= NOW() - (%s || ' minutes')::interval
                    GROUP BY c.camera_id, c.name, c.latitude, c.longitude, c.speed_limit_kmh; \
                    """
            cur.execute(query, (minutes, str(minutes)))
            rows = cur.fetchall()

            features = []
            for row in rows:
                # Classify congestion intensity
                density = float(row["vehicles_per_minute"])
                intensity = "LOW" if density < 10 else ("MEDIUM" if density < 25 else "HIGH")

                features.append({
                    "camera_id": row["camera_id"],
                    "name": row["name"],
                    "lat": row["latitude"],
                    "lon": row["longitude"],
                    "speed_limit": row["speed_limit_kmh"],
                    "vehicle_count": row["vehicle_count"],
                    "vehicles_per_minute": density,
                    "congestion_intensity": intensity
                })

            return {"time_window_minutes": minutes, "total_nodes": len(features), "nodes": features}
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# ROUTE 5: Active Alerts Log
# ----------------------------------------------------------------------------
@app.get("/api/v1/alerts")
def get_recent_alerts(limit: int = 20):
    conn = engine.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                        SELECT a.alert_id,
                               a.plate_text,
                               a.camera_id,
                               c.name AS camera_name,
                               a.confidence,
                               a.event_time::text AS timestamp,
                    b.reason,
                    b.alert_priority
                        FROM alerts_log a
                            JOIN cameras c
                        ON a.camera_id = c.camera_id
                            JOIN blacklist b ON a.plate_text = b.plate_text
                        ORDER BY a.event_time DESC
                            LIMIT %s;
                        """, (limit,))
            return cur.fetchall()
    finally:
        conn.close()


# ============================================================================
# 5. WEBSOCKET ENDPOINT (Live Push to Frontend)
# ============================================================================
@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await alert_manager.connect(websocket)
    try:
        while True:
            # Keep socket alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        alert_manager.disconnect(websocket)
# ============================================================================
# 1. CAMERA INFRASTRUCTURE MANAGEMENT (For Initial Map Plotting)
# ============================================================================
@app.get("/api/v1/cameras")
def get_all_cameras():
    """
    Returns all registered cameras and coordinates for the frontend to render static map pins.
    """
    conn = engine.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    camera_id, 
                    name, 
                    latitude, 
                    longitude, 
                    direction_heading, 
                    speed_limit_kmh, 
                    is_active, 
                    created_at::text AS created_at
                FROM cameras
                ORDER BY camera_id ASC;
            """)
            cameras = cur.fetchall()
            return {"total_cameras": len(cameras), "cameras": cameras}
    finally:
        conn.close()

@app.post("/api/v1/cameras", status_code=201)
def register_camera(camera: CameraCreateSchema):
    """
    Adds a new camera node to the network.
    """
    conn = engine.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO cameras (camera_id, name, latitude, longitude, direction_heading, speed_limit_kmh)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (camera_id) DO UPDATE 
                SET name = EXCLUDED.name,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    direction_heading = EXCLUDED.direction_heading,
                    speed_limit_kmh = EXCLUDED.speed_limit_kmh
                RETURNING camera_id;
            """, (
                camera.camera_id,
                camera.name,
                camera.latitude,
                camera.longitude,
                camera.direction_heading,
                camera.speed_limit_kmh
            ))
            conn.commit()
            return {"status": "SUCCESS", "camera_id": camera.camera_id}
    finally:
        conn.close()

# ============================================================================
# 2. VEHICLE SEARCH AUTOCOMPLETE & RECENT DETECTIONS
# ============================================================================

@app.get("/api/v1/vehicles/search-suggestions")
def get_plate_suggestions(query: str = Query(..., min_length=2, example="TN09")):
    """
    Powers search bar autocomplete dropdown in the frontend.
    """
    clean_q = query.upper().strip()
    conn = engine.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT plate_text, vehicle_class, vehicle_color
                FROM camera_events
                WHERE plate_text ILIKE %s || '%%'
                LIMIT 8;
            """, (clean_q,))
            suggestions = cur.fetchall()
            return {"query": clean_q, "results": suggestions}
    finally:
        conn.close()

@app.get("/api/v1/cameras/{camera_id}/recent-feed")
def get_camera_recent_feed(camera_id: str, limit: int = 10):
    """
    Returns the latest plate detections for a specific camera (for UI sidebar on camera click).
    """
    conn = engine.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    event_id,
                    plate_text,
                    ocr_confidence,
                    vehicle_class,
                    vehicle_color,
                    plate_crop_url,
                    event_time::text AS timestamp
                FROM camera_events
                WHERE camera_id = %s
                ORDER BY event_time DESC
                LIMIT %s;
            """, (camera_id, limit))
            records = cur.fetchall()
            return {"camera_id": camera_id, "recent_events": records}
    finally:
        conn.close()

# ============================================================================
# 3. BLACKLIST / WATCHLIST MANAGEMENT (For Police Admin Controls)
# ============================================================================

@app.get("/api/v1/blacklist")
def get_blacklist():
    """
    Returns all registered watchlist vehicles.
    """
    conn = engine.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    plate_text, 
                    reason, 
                    alert_priority, 
                    owner_name, 
                    vehicle_description, 
                    added_at::text AS added_at,
                    is_active
                FROM blacklist
                ORDER BY added_at DESC;
            """)
            return cur.fetchall()
    finally:
        conn.close()

@app.post("/api/v1/blacklist", status_code=201)
def add_to_blacklist(entry: BlacklistCreateSchema):
    """
    Adds a new stolen/wanted plate to the real-time watchlist.
    """
    conn = engine.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO blacklist (plate_text, reason, alert_priority, owner_name, vehicle_description)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (plate_text) DO UPDATE 
                SET reason = EXCLUDED.reason,
                    alert_priority = EXCLUDED.alert_priority,
                    owner_name = EXCLUDED.owner_name,
                    vehicle_description = EXCLUDED.vehicle_description,
                    is_active = TRUE;
            """, (
                entry.plate_text.upper().strip(),
                entry.reason,
                entry.alert_priority,
                entry.owner_name,
                entry.vehicle_description
            ))
            conn.commit()
            return {"status": "SUCCESS", "plate_text": entry.plate_text.upper().strip()}
    finally:
        conn.close()

@app.delete("/api/v1/blacklist/{plate_text}")
def remove_from_blacklist(plate_text: str):
    """
    Deletes or deactivates a plate from the watchlist.
    """
    conn = engine.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM blacklist WHERE plate_text = %s;", (plate_text.upper().strip(),))
            conn.commit()
            return {"status": "DELETED", "plate_text": plate_text.upper().strip()}
    finally:
        conn.close()

# ============================================================================
# 4. SYSTEM SUMMARY METRICS (For Dashboard Top Header)
# ============================================================================

@app.get("/api/v1/analytics/overview")
def get_system_overview():
    """
    Returns high-level KPI cards for the top dashboard bar.
    """
    conn = engine.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM cameras WHERE is_active = TRUE) AS active_cameras,
                    (SELECT COUNT(*) FROM camera_events WHERE event_time >= NOW() - INTERVAL '24 hours') AS detections_24h,
                    (SELECT COUNT(*) FROM blacklist WHERE is_active = TRUE) AS active_watchlist_count,
                    (SELECT COUNT(*) FROM alerts_log WHERE is_acknowledged = FALSE) AS unacknowledged_alerts;
            """)
            stats = cur.fetchone()
            return stats
    finally:
        conn.close()

@app.get("/api/v1/analytics/od-matrix")
def get_origin_destination_matrix(hours: int = 4, min_trips: int = 2):
    """
    Computes Origin-Destination (OD) vehicle counts and average corridor speeds
    between sequential camera sightings.
    """
    conn = engine.get_db_connection()
    try:
        with conn.cursor() as cur:
            # Self-join camera_events to find transitions of the same plate between consecutive cameras
            query = """
            WITH ordered_sightings AS (
                SELECT 
                    plate_text,
                    camera_id,
                    event_time,
                    LEAD(camera_id) OVER (PARTITION BY plate_text ORDER BY event_time ASC) AS next_camera_id,
                    LEAD(event_time) OVER (PARTITION BY plate_text ORDER BY event_time ASC) AS next_event_time
                FROM camera_events
                WHERE event_time >= NOW() - (%s || ' hours')::interval
            )
            SELECT 
                s.camera_id AS origin_camera_id,
                c1.name AS origin_name,
                c1.latitude AS origin_lat,
                c1.longitude AS origin_lon,
                s.next_camera_id AS destination_camera_id,
                c2.name AS destination_name,
                c2.latitude AS destination_lat,
                c2.longitude AS destination_lon,
                COUNT(*) AS total_trips,
                ROUND(AVG(EXTRACT(EPOCH FROM (s.next_event_time - s.event_time)) / 60.0)::numeric, 1) AS avg_duration_minutes
            FROM ordered_sightings s
            JOIN cameras c1 ON s.camera_id = c1.camera_id
            JOIN cameras c2 ON s.next_camera_id = c2.camera_id
            WHERE s.next_camera_id IS NOT NULL 
              AND s.camera_id != s.next_camera_id
            GROUP BY s.camera_id, c1.name, c1.latitude, c1.longitude,
                     s.next_camera_id, c2.name, c2.latitude, c2.longitude
            HAVING COUNT(*) >= %s
            ORDER BY total_trips DESC
            LIMIT 20;
            """
            cur.execute(query, (str(hours), min_trips))
            rows = cur.fetchall()
            return {"time_window_hours": hours, "corridors": rows}
    finally:
        conn.close()

# ============================================================================
# 5. ANALYTICS API ROUTES
# ============================================================================

@app.get("/api/v1/analytics/summary", tags=["Analytics"])
def get_analytics_summary():
    """
    Returns aggregated traffic metrics for the City EYE Analytics Dashboard.
    """
    try:
        data = engine.get_24h_analytics_summary()
        return data
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate analytics summary: {str(e)}"
        )

@app.get("/api/v1/tracking/predict/{plate_number}")
async def predict_escape_route(plate_number: str):
    """
    Calculates the probable escape vector and downstream intercept 
    chokepoints for a given target license plate.
    """
    try:
        # Call the math engine
        prediction = engine.get_predictive_intercept(plate_number)
        
        # Handle the edge case where the car was only seen once
        if prediction.get("status") == "insufficient_data":
            raise HTTPException(
                status_code=404, 
                detail="Insufficient tracking data. At least 2 sightings required to calculate velocity vector."
            )
            
        # Return the JSON payload containing the cone polygon and intercept points
        return prediction
        
    except HTTPException:
        raise
    except Exception as e:
        # Catch any database or math errors
        print(f"Prediction Error for plate {plate_number}: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error during predictive geodesic calculation."
        )