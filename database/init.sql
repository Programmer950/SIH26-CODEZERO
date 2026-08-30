-- ============================================================================
-- 1. EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS postgis;          -- For spatial geometry and GPS distance
CREATE EXTENSION IF NOT EXISTS pg_trgm;          -- For GIN trigram fast fuzzy string matching
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;    -- For Levenshtein edit distance calculations

-- ============================================================================
-- 2. CAMERA INFRASTRUCTURE TABLE
-- ============================================================================
-- Stores static geographical ground truth for all city-wide ANPR/CCTV cameras
CREATE TABLE cameras (
    camera_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(Point, 4326),                  -- Spatial point representation
    direction_heading INT,                       -- Camera heading in degrees (0-360)
    speed_limit_kmh INT DEFAULT 50,              -- Road segment speed limit
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Automatically populate PostGIS Point geometry on camera insert/update
CREATE OR REPLACE FUNCTION update_camera_geom()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_camera_geom
BEFORE INSERT OR UPDATE ON cameras
FOR EACH ROW
EXECUTE FUNCTION update_camera_geom();

-- ============================================================================
-- 3. RAW SIGHTING EVENTS TABLE (High-Throughput Ingestion)
-- ============================================================================
-- Receives lightweight JSON events from edge YOLO/ANPR workers
CREATE TABLE camera_events (
    event_id BIGSERIAL PRIMARY KEY,
    camera_id VARCHAR(50) NOT NULL REFERENCES cameras(camera_id) ON DELETE CASCADE,
    plate_text VARCHAR(20) NOT NULL,
    ocr_confidence FLOAT NOT NULL,
    vehicle_class VARCHAR(30),                   -- 'Sedan', 'SUV', 'Truck', 'Bike'
    vehicle_color VARCHAR(30),                   -- 'White', 'Black', 'Silver', 'Red'
    embedding JSONB,                             -- 128-d or 512-d Re-ID feature vector
    plate_crop_url TEXT,                         -- URL/path to static crop snapshot
    event_time TIMESTAMPTZ NOT NULL,             -- Edge camera sighting timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 4. BLACKLIST & WATCHLIST TABLE
-- ============================================================================
-- Checked synchronously at ingestion time for instant law-enforcement alerting
CREATE TABLE blacklist (
    plate_text VARCHAR(20) PRIMARY KEY,
    reason VARCHAR(255) NOT NULL,                -- 'Stolen Vehicle FIR #882', 'Hit and Run'
    alert_priority VARCHAR(20) DEFAULT 'HIGH',   -- 'CRITICAL', 'HIGH', 'MEDIUM'
    owner_name VARCHAR(100),
    vehicle_description VARCHAR(150),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- ============================================================================
-- 5. REAL-TIME ALERTS LOG
-- ============================================================================
-- Records all triggered watchlist detections
CREATE TABLE alerts_log (
    alert_id BIGSERIAL PRIMARY KEY,
    plate_text VARCHAR(20) NOT NULL,
    camera_id VARCHAR(50) NOT NULL REFERENCES cameras(camera_id) ON DELETE CASCADE,
    confidence FLOAT,
    event_time TIMESTAMPTZ NOT NULL,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 6. PERFORMANCE INDEXING STRATEGY
-- ============================================================================

-- 1. GIN Trigram Index: Enables fast fuzzy queries (e.g. TN09AB1234 matches TN09A81234)
CREATE INDEX idx_events_plate_trgm ON camera_events USING gin (plate_text gin_trgm_ops);

-- 2. Compound Index for Time-Window Filtering by Camera
CREATE INDEX idx_events_time_cam ON camera_events (event_time DESC, camera_id);

-- 3. Standard B-Tree for exact plate + time lookups
CREATE INDEX idx_events_plate_time ON camera_events (plate_text, event_time ASC);

-- 4. PostGIS Spatial Index for Camera Nodes
CREATE INDEX idx_cameras_geom ON cameras USING gist (geom);

-- 5. Alerts Chronological Index
CREATE INDEX idx_alerts_time ON alerts_log (event_time DESC);

-- ============================================================================
-- 7. SEED DATA: 100 CHENNAI ANPR CAMERA NODES
-- ============================================================================
-- Note: 'geom', 'is_active', and 'created_at' will auto-populate via defaults and triggers.

INSERT INTO cameras (camera_id, name, latitude, longitude, direction_heading, speed_limit_kmh) VALUES 

-- CORRIDOR 1: Anna Salai (Mount Road) - City Center to South
('CAM_AN_01', 'Chennai Central Station Junction', 13.0827, 80.2707, 180, 40),
('CAM_AN_02', 'Pallavan Salai / Simpson', 13.0722, 80.2678, 190, 40),
('CAM_AN_03', 'LIC Building Junction', 13.0645, 80.2642, 210, 40),
('CAM_AN_04', 'Spencer Plaza Signal', 13.0610, 80.2605, 215, 40),
('CAM_AN_05', 'Gemini Flyover (Anna Flyover) Underpass', 13.0535, 80.2504, 215, 40),
('CAM_AN_06', 'Teynampet Signal (DMS)', 13.0416, 80.2443, 200, 40),
('CAM_AN_07', 'Nandanam Signal', 13.0315, 80.2371, 205, 40),
('CAM_AN_08', 'Saidapet Panagal Maligai', 13.0210, 80.2265, 210, 40),
('CAM_AN_09', 'Little Mount Metro', 13.0135, 80.2198, 220, 50),
('CAM_AN_10', 'Guindy Kathipara Cloverleaf', 13.0067, 80.2025, 240, 50),

-- CORRIDOR 2: OMR (Rajiv Gandhi Salai) - IT Corridor
('CAM_OM_01', 'Madhya Kailash Junction', 13.0076, 80.2449, 170, 50),
('CAM_OM_02', 'Tidel Park Signal', 12.9895, 80.2488, 175, 50),
('CAM_OM_03', 'SRP Tools Junction', 12.9790, 80.2483, 180, 50),
('CAM_OM_04', 'Perungudi Toll Plaza', 12.9645, 80.2445, 185, 60),
('CAM_OM_05', 'Thoraipakkam Radial Road Jn', 12.9365, 80.2315, 190, 50),
('CAM_OM_06', 'Karapakkam Signal', 12.9165, 80.2290, 185, 50),
('CAM_OM_07', 'Sholinganallur Junction', 12.9015, 80.2272, 190, 50),
('CAM_OM_08', 'Navalur Toll Plaza', 12.8465, 80.2245, 180, 60),
('CAM_OM_09', 'Siruseri SIPCOT Entrance', 12.8280, 80.2195, 180, 50),
('CAM_OM_10', 'Kelambakkam Junction', 12.7915, 80.2205, 185, 50),

-- CORRIDOR 3: GST Road (Grand Southern Trunk) - Airport & Suburbs
('CAM_GS_01', 'St Thomas Mount Station', 12.9940, 80.1945, 210, 50),
('CAM_GS_02', 'Meenambakkam Airport Entry', 12.9815, 80.1765, 215, 50),
('CAM_GS_03', 'Pallavaram Radial Road Jn', 12.9675, 80.1475, 220, 50),
('CAM_GS_04', 'Chromepet MIT Gate', 12.9515, 80.1405, 215, 50),
('CAM_GS_05', 'Tambaram Hindu Mission Jn', 12.9245, 80.1170, 210, 50),
('CAM_GS_06', 'Perungalathur Bypass Entry', 12.8985, 80.0955, 215, 50),
('CAM_GS_07', 'Vandalur Zoo Junction', 12.8840, 80.0825, 210, 50),
('CAM_GS_08', 'Guduvanchery Signal', 12.8445, 80.0575, 215, 60),
('CAM_GS_09', 'SRM University Potheri', 12.8235, 80.0440, 220, 60),
('CAM_GS_10', 'Paranur Toll Plaza (Chengalpattu)', 12.7235, 79.9925, 210, 80),

-- CORRIDOR 4: Inner Ring Road (100ft Road) - West Arc
('CAM_IR_01', 'Ashok Pillar Junction', 13.0360, 80.2115, 340, 50),
('CAM_IR_02', 'Vadapalani Signal', 13.0505, 80.2118, 350, 40),
('CAM_IR_03', 'Koyambedu Roundabout (CMBT)', 13.0732, 80.1937, 360, 50),
('CAM_IR_04', 'Thirumangalam Junction', 13.0845, 80.1930, 10, 50),
('CAM_IR_05', 'Anna Nagar Roundabout', 13.0855, 80.2115, 90, 40),
('CAM_IR_06', 'Retteri Junction', 13.1255, 80.2135, 45, 50),
('CAM_IR_07', 'Madhavaram Roundabout', 13.1465, 80.2335, 90, 50),
('CAM_IR_08', 'Moolakadai Junction', 13.1275, 80.2445, 120, 50),
('CAM_IR_09', 'Perambur Loco Works', 13.1095, 80.2375, 180, 40),
('CAM_IR_10', 'Padi Flyover', 13.0945, 80.1870, 270, 50),

-- CORRIDOR 5: Poonamallee High Road - Central to West
('CAM_PH_01', 'Egmore Commissioner Office', 13.0775, 80.2625, 270, 40),
('CAM_PH_02', 'Kilpauk Medical College', 13.0785, 80.2435, 260, 40),
('CAM_PH_03', 'Aminjikarai Signal', 13.0760, 80.2235, 265, 40),
('CAM_PH_04', 'Anna Arch Junction', 13.0755, 80.2155, 270, 40),
('CAM_PH_05', 'Maduravoyal Bypass Junction', 13.0645, 80.1650, 260, 60),
('CAM_PH_06', 'Porur Toll Plaza', 13.0405, 80.1485, 250, 60),
('CAM_PH_07', 'Vanagaram Signal', 13.0560, 80.1435, 265, 50),
('CAM_PH_08', 'Saveetha Dental College', 13.0515, 80.1235, 270, 50),
('CAM_PH_09', 'Poonamallee Trunk Road', 13.0485, 80.1015, 260, 50),
('CAM_PH_10', 'Nazarathpet Outer Ring', 13.0375, 80.0615, 250, 60),

-- CORRIDOR 6: ECR (East Coast Road) - Coastline
('CAM_EC_01', 'Thiruvanmiyur RTO', 12.9865, 80.2595, 180, 50),
('CAM_EC_02', 'Kottivakkam Signal', 12.9685, 80.2605, 175, 50),
('CAM_EC_03', 'Palavakkam Signal', 12.9565, 80.2595, 180, 50),
('CAM_EC_04', 'Neelankarai Junction', 12.9435, 80.2565, 175, 50),
('CAM_EC_05', 'Injambakkam ECR', 12.9165, 80.2485, 185, 50),
('CAM_EC_06', 'Akkarai Water Tank (ECR-OMR Link)', 12.8915, 80.2425, 190, 50),
('CAM_EC_07', 'Uthandi Toll Plaza', 12.8685, 80.2395, 180, 60),
('CAM_EC_08', 'Muttukadu Boat House', 12.8125, 80.2425, 195, 60),
('CAM_EC_09', 'Kovalam Junction', 12.7885, 80.2485, 200, 60),
('CAM_EC_10', 'Mahabalipuram Bypass', 12.6325, 80.1875, 210, 60),

-- CORRIDOR 7: Chennai Outer Ring Road (ORR) & Bypass
('CAM_OR_01', 'Puzhal Toll Plaza', 13.1555, 80.1985, 180, 80),
('CAM_OR_02', 'Ambattur Industrial Estate', 13.0975, 80.1615, 185, 60),
('CAM_OR_03', 'Avadi Junction', 13.1165, 80.1015, 270, 50),
('CAM_OR_04', 'Pattabiram Signal', 13.1235, 80.0615, 260, 50),
('CAM_OR_05', 'Mangadu ORR Junction', 13.0235, 80.0915, 180, 80),
('CAM_OR_06', 'Kundrathur Bypass', 12.9965, 80.0985, 175, 80),
('CAM_OR_07', 'Mudichur ORR', 12.9165, 80.0615, 190, 80),
('CAM_OR_08', 'Vandalur ORR Toll', 12.8885, 80.0715, 160, 80),
('CAM_OR_09', 'Minjur Toll Plaza', 13.2735, 80.2585, 180, 80),
('CAM_OR_10', 'Manali Expressway', 13.1815, 80.2715, 190, 60),

-- CORRIDOR 8: Adyar, Mylapore, and Marina (South-East Hubs)
('CAM_SE_01', 'Adyar Signal', 13.0065, 80.2575, 360, 40),
('CAM_SE_02', 'Besant Nagar Church', 12.9985, 80.2715, 90, 40),
('CAM_SE_03', 'Thiru Vi Ka Bridge', 13.0165, 80.2585, 10, 50),
('CAM_SE_04', 'Greenways Road MRTS', 13.0235, 80.2585, 350, 40),
('CAM_SE_05', 'Mandaveli Depot', 13.0315, 80.2625, 360, 40),
('CAM_SE_06', 'Mylapore Luz Corner', 13.0365, 80.2665, 10, 40),
('CAM_SE_07', 'Marina Beach Lighthouse', 13.0415, 80.2795, 350, 40),
('CAM_SE_08', 'Vivekanandar Illam', 13.0495, 80.2815, 355, 40),
('CAM_SE_09', 'Santhome Church', 13.0335, 80.2775, 180, 40),
('CAM_SE_10', 'Napier Bridge', 13.0675, 80.2825, 340, 50),

-- CORRIDOR 9: North Chennai (Commercial & Port Routes)
('CAM_NC_01', 'Royapuram Bridge', 13.1065, 80.2925, 360, 40),
('CAM_NC_02', 'Kasimedu Fishing Harbour', 13.1235, 80.2975, 10, 40),
('CAM_NC_03', 'Tiruvottiyur Theradi', 13.1615, 80.3015, 15, 40),
('CAM_NC_04', 'Ennore Port Road', 13.2015, 80.3115, 20, 60),
('CAM_NC_05', 'Mint Junction', 13.1045, 80.2785, 320, 40),
('CAM_NC_06', 'Washermanpet Metro', 13.1115, 80.2865, 330, 40),
('CAM_NC_07', 'Vyasarpadi Jeeva', 13.1165, 80.2585, 270, 40),
('CAM_NC_08', 'Basin Bridge', 13.0965, 80.2715, 260, 40),
('CAM_NC_09', 'Tondiarpet Signal', 13.1315, 80.2885, 350, 40),
('CAM_NC_10', 'Chennai Port Gate 1', 13.0935, 80.2945, 180, 40),

-- CORRIDOR 10: Suburban Link Roads & Key Flyovers
('CAM_SL_01', 'Tharamani Link Road', 12.9785, 80.2285, 270, 50),
('CAM_SL_02', 'Velachery Vijayanagar', 12.9735, 80.2215, 280, 40),
('CAM_SL_03', 'Medavakkam Junction', 12.9235, 80.1875, 180, 50),
('CAM_SL_04', 'Pallikaranai Marshland', 12.9435, 80.2075, 190, 50),
('CAM_SL_05', 'Kamarajapuram Signal', 12.9165, 80.1585, 260, 40),
('CAM_SL_06', 'Madipakkam Koot Road', 12.9645, 80.1985, 270, 40),
('CAM_SL_07', 'Keelkattalai Signal', 12.9555, 80.1815, 260, 40),
('CAM_SL_08', 'Mugalivakkam Signal', 13.0235, 80.1615, 270, 40),
('CAM_SL_09', 'Iyyappanthangal Depot', 13.0365, 80.1365, 280, 40),
('CAM_SL_10', 'Kundrathur Murugan Temple', 12.9915, 80.0985, 210, 40)

ON CONFLICT (camera_id) DO NOTHING;

-- ============================================================================
-- 8. PROBABILISTIC MARKOV TRANSITION MATRIX (First-Order)
-- ============================================================================
DROP MATERIALIZED VIEW IF EXISTS markov_matrix_v2 CASCADE;

CREATE MATERIALIZED VIEW IF NOT EXISTS markov_matrix AS
WITH sequential_hits AS (
    SELECT 
        camera_id AS current_camera,
        LEAD(camera_id) OVER (PARTITION BY plate_text ORDER BY event_time) AS next_camera
    FROM camera_events
),
transition_counts AS (
    SELECT current_camera, next_camera, COUNT(*) as weight
    FROM sequential_hits
    WHERE next_camera IS NOT NULL
    GROUP BY current_camera, next_camera
)
SELECT 
    current_camera, 
    next_camera, 
    weight::FLOAT / SUM(weight) OVER (PARTITION BY current_camera) AS probability
FROM transition_counts;

CREATE INDEX IF NOT EXISTS idx_markov_current ON markov_matrix(current_camera);