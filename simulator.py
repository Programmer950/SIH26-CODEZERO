import time
import json
import random
import math
import psycopg2
import requests
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone, timedelta

# ==============================================================================
# CONFIGURATION
# ==============================================================================
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "SIH26",
    "user": "postgres",
    "password": "root"
}
API_URL_EVENTS = "http://localhost:8000/api/v1/events"

# 75 REAL CHENNAI CAMERA NODES (Assuming the list from previous step is here)
# Keeping this abbreviated for snippet, but LEAVE YOUR 75 CAMERAS EXACTLY AS THEY ARE
CHENNAI_75_CAMERAS = [
    ("CAM_01_KOYAMBEDU_JN", "Koyambedu", 13.0732, 80.1937, 50),
    ("CAM_09_VADAPALANI_JN", "Vadapalani", 13.0500, 80.2120, 50),
    ("CAM_10_ASHOK_PILLAR", "Ashok Pillar", 13.0340, 80.2110, 50),
    ("CAM_13_KATHIPARA_FLY", "Kathipara", 13.0067, 80.2025, 60),
    ("CAM_15_MEENAMBAKKAM", "Meenambakkam", 12.9880, 80.1770, 60),
    ("CAM_16_AIRPORT_ENTRY", "Airport", 12.9820, 80.1640, 40),
    ("CAM_31_MADHYA_KAILASH", "Madhya Kailash", 13.0070, 80.2530, 50),
    ("CAM_32_TIDEL_PARK", "Tidel Park", 12.9890, 80.2490, 60),
    ("CAM_33_PERUNGUDI_TOLL", "Perungudi Toll", 12.9640, 80.2440, 60),
    ("CAM_34_THORAIPAKKAM", "Thoraipakkam", 12.9360, 80.2310, 60),
    ("CAM_35_SHOLINGANALLUR", "Sholinganallur", 12.9010, 80.2270, 60),
    ("CAM_41_CHENNAI_CENTRAL", "Central", 13.0820, 80.2750, 40),
    ("CAM_42_EGMORE_STATION", "Egmore", 13.0780, 80.2610, 40),
    ("CAM_27_GEMINI_FLY", "Gemini", 13.0510, 80.2520, 50),
    ("CAM_29_NANDANAM_SIG", "Nandanam", 13.0310, 80.2380, 50),
    ("CAM_30_SAIDAPET_METRO", "Saidapet", 13.0230, 80.2250, 50)
] # NOTE: Keep your full 75 list here in your actual file!

# Realistic City Corridors (Cars will pick one and travel down it)
TRAFFIC_CORRIDORS = [
    # 1. Airport Run (West to South)
    ["CAM_01_KOYAMBEDU_JN", "CAM_09_VADAPALANI_JN", "CAM_10_ASHOK_PILLAR", "CAM_13_KATHIPARA_FLY", "CAM_15_MEENAMBAKKAM", "CAM_16_AIRPORT_ENTRY"],
    # 2. OMR IT Corridor (North to South)
    ["CAM_31_MADHYA_KAILASH", "CAM_32_TIDEL_PARK", "CAM_33_PERUNGUDI_TOLL", "CAM_34_THORAIPAKKAM", "CAM_35_SHOLINGANALLUR"],
    # 3. Anna Salai Commute (Central to South)
    ["CAM_41_CHENNAI_CENTRAL", "CAM_42_EGMORE_STATION", "CAM_27_GEMINI_FLY", "CAM_29_NANDANAM_SIG", "CAM_30_SAIDAPET_METRO", "CAM_13_KATHIPARA_FLY"]
]

TYPO_MAP = {'B': '8', '8': 'B', '0': 'D', 'D': '0', 'Z': '2', '2': 'Z', 'S': '5', '5': 'S'}
VEHICLE_CLASSES = ["SUV", "Sedan", "Hatchback", "Commercial Truck", "Motorcycle", "Auto-Rickshaw"]
COLORS = ["White", "Silver", "Black", "Grey", "Red", "Blue"]

def get_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def generate_random_plate():
    districts = ["01", "02", "04", "07", "09", "10", "14", "18", "22"]
    letters = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=2))
    digits = f"{random.randint(1000, 9999)}"
    return f"TN{random.choice(districts)}{letters}{digits}"

def generate_synthetic_embedding():
    vec = [random.uniform(-1.0, 1.0) for _ in range(3)]
    mag = math.sqrt(sum(v**2 for v in vec))
    return [round(v / mag, 4) for v in vec]

def get_target_traffic_volume():
    """Returns the number of active cars that should be on the road right now based on the clock."""
    hour = datetime.now().hour
    if 8 <= hour <= 11:
        return 80  # Morning Rush (School/Office)
    elif 17 <= hour <= 20:
        return 100 # Evening Rush
    elif 12 <= hour <= 16:
        return 45  # Mid-day lull
    elif 21 <= hour <= 23:
        return 25  # Night traffic
    else:
        return 10  # Midnight to 7AM (Ghost town)

def run_continuous_traffic_stream():
    print("\n[4/4] 🟢 STARTING LIFECYCLE TRAFFIC ENGINE (Ctrl+C to stop)...")
    
    active_vehicles = []
    session = requests.Session()
    
    # Track the stolen car separately
    stolen_car = {
        "plate": "TN09AB9999", "route": TRAFFIC_CORRIDORS[2], 
        "step": 0, "next_appearance": time.time() + 5
    }

    try:
        while True:
            now_iso = datetime.now(timezone.utc).isoformat()
            now_ts = time.time()
            target_volume = get_target_traffic_volume()

            # 1. Spawn new vehicles if the city is below the target traffic volume for this hour
            while len(active_vehicles) < target_volume:
                route = random.choice(TRAFFIC_CORRIDORS)
                active_vehicles.append({
                    "plate": generate_random_plate(),
                    "route": route,
                    "step": 0,
                    # Stagger their first appearance slightly
                    "next_appearance": now_ts + random.uniform(0, 15),
                    "v_class": random.choice(VEHICLE_CLASSES),
                    "v_color": random.choice(COLORS),
                    "embed": generate_synthetic_embedding()
                })

            pushed_count = 0
            active_plates = []

            # 2. Move active commuters down their specific routes
            for vehicle in active_vehicles[:]:
                if now_ts >= vehicle["next_appearance"]:
                    # It's time for this car to pass a camera
                    cam_id = vehicle["route"][vehicle["step"]]
                    
                    payload = {
                        "camera_id": cam_id,
                        "plate_text": vehicle["plate"],
                        "ocr_confidence": round(random.uniform(0.85, 0.99), 2),
                        "timestamp": now_iso,
                        "vehicle_class": vehicle["v_class"],
                        "vehicle_color": vehicle["v_color"],
                        "embedding": vehicle["embed"]
                    }
                    
                    try:
                        session.post(API_URL_EVENTS, json=payload, timeout=2)
                        pushed_count += 1
                        active_plates.append(vehicle["plate"])
                    except requests.exceptions.RequestException:
                        pass
                    
                    # Advance the car to the next camera
                    vehicle["step"] += 1
                    
                    # If it finished the route, despawn it
                    if vehicle["step"] >= len(vehicle["route"]):
                        active_vehicles.remove(vehicle)
                    else:
                        # Demo pacing: Wait 15 to 35 seconds to reach the next camera
                        # (Fast enough to show judges live tracking, slow enough to feel like travel)
                        vehicle["next_appearance"] = now_ts + random.uniform(15, 35)

            # 3. Handle the stolen car independently
            if now_ts >= stolen_car["next_appearance"] and stolen_car["step"] < len(stolen_car["route"]):
                cam_id = stolen_car["route"][stolen_car["step"]]
                payload = {
                    "camera_id": cam_id, "plate_text": stolen_car["plate"],
                    "ocr_confidence": 0.98, "timestamp": now_iso,
                    "vehicle_class": "SUV", "vehicle_color": "Black",
                    "embedding": generate_synthetic_embedding()
                }
                try:
                    res = session.post(API_URL_EVENTS, json=payload, timeout=3)
                    print(f" 🚨 WATCHLIST HIT POSTED: {stolen_car['plate']} at {cam_id} | Status: {res.status_code}")
                except requests.exceptions.RequestException:
                    pass
                
                stolen_car["step"] += 1
                stolen_car["next_appearance"] = now_ts + random.uniform(20, 45) # Stolen car drives slightly slower

            # Log system state
            if pushed_count > 0:
                print(f" 📡 {now_iso[-14:-6]} | Hour: {datetime.now().hour}:00 | Volume: {len(active_vehicles)} cars | Events Pushed: {pushed_count}")
                # Print a few active plates so you have something to search in the UI
                if len(active_plates) > 0:
                    print(f"    🔍 Traceable Plates: {', '.join(active_plates[:3])}")
            
            time.sleep(1) # Loop tick speed
            
    except KeyboardInterrupt:
        print("\n🛑 Simulation Stopped.")

if __name__ == "__main__":
    # Ensure you keep your seed_cameras() and prime_heatmap() functions running before the live stream!
    # seed_cameras_and_blacklist()
    # prime_heatmap_traffic()
    run_continuous_traffic_stream()