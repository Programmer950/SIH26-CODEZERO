import time
import math
import random
import threading
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Set, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


# =============================================================================
# 1. CONFIGURATION & PROFILES
# =============================================================================

API_URL = "http://localhost:8000/api/v1/events"
TICK_RATE = 0.5  # Simulation tick rate in seconds

TRAFFIC_PROFILES = {
    "demo": 50,
    "light": 200,
    "normal": 500,
    "busy": 1500,
    "rush_hour": 3000
}

VEHICLE_CLASSES = [
    ("Motorcycle", 40),
    ("Hatchback", 20),
    ("Sedan", 15),
    ("SUV", 15),
    ("Auto-Rickshaw", 7),
    ("Commercial Truck", 3),
]

VEHICLE_COLORS = [
    "White",
    "Black",
    "Silver",
    "Grey",
    "Blue",
    "Red",
    "Brown"
]


# =============================================================================
# 2. CAMERA GEOGRAPHICAL GROUND TRUTH (100 CHENNAI ANPR NODES)
# =============================================================================

CAMERA_COORDINATES: Dict[str, Tuple[float, float]] = {
    # CORRIDOR 1: Anna Salai (Mount Road)
    "CAM_AN_01": (13.0827, 80.2707), "CAM_AN_02": (13.0722, 80.2678),
    "CAM_AN_03": (13.0645, 80.2642), "CAM_AN_04": (13.0610, 80.2605),
    "CAM_AN_05": (13.0535, 80.2504), "CAM_AN_06": (13.0416, 80.2443),
    "CAM_AN_07": (13.0315, 80.2371), "CAM_AN_08": (13.0210, 80.2265),
    "CAM_AN_09": (13.0135, 80.2198), "CAM_AN_10": (13.0067, 80.2025),

    # CORRIDOR 2: OMR (Rajiv Gandhi Salai)
    "CAM_OM_01": (13.0076, 80.2449), "CAM_OM_02": (12.9895, 80.2488),
    "CAM_OM_03": (12.9790, 80.2483), "CAM_OM_04": (12.9645, 80.2445),
    "CAM_OM_05": (12.9365, 80.2315), "CAM_OM_06": (12.9165, 80.2290),
    "CAM_OM_07": (12.9015, 80.2272), "CAM_OM_08": (12.8465, 80.2245),
    "CAM_OM_09": (12.8280, 80.2195), "CAM_OM_10": (12.7915, 80.2205),

    # CORRIDOR 3: GST Road (Grand Southern Trunk)
    "CAM_GS_01": (12.9940, 80.1945), "CAM_GS_02": (12.9815, 80.1765),
    "CAM_GS_03": (12.9675, 80.1475), "CAM_GS_04": (12.9515, 80.1405),
    "CAM_GS_05": (12.9245, 80.1170), "CAM_GS_06": (12.8985, 80.0955),
    "CAM_GS_07": (12.8840, 80.0825), "CAM_GS_08": (12.8445, 80.0575),
    "CAM_GS_09": (12.8235, 80.0440), "CAM_GS_10": (12.7235, 79.9925),

    # CORRIDOR 4: Inner Ring Road (100ft Road)
    "CAM_IR_01": (13.0360, 80.2115), "CAM_IR_02": (13.0505, 80.2118),
    "CAM_IR_03": (13.0732, 80.1937), "CAM_IR_04": (13.0845, 80.1930),
    "CAM_IR_05": (13.0855, 80.2115), "CAM_IR_06": (13.1255, 80.2135),
    "CAM_IR_07": (13.1465, 80.2335), "CAM_IR_08": (13.1275, 80.2445),
    "CAM_IR_09": (13.1095, 80.2375), "CAM_IR_10": (13.0945, 80.1870),

    # CORRIDOR 5: Poonamallee High Road
    "CAM_PH_01": (13.0775, 80.2625), "CAM_PH_02": (13.0785, 80.2435),
    "CAM_PH_03": (13.0760, 80.2235), "CAM_PH_04": (13.0755, 80.2155),
    "CAM_PH_05": (13.0645, 80.1650), "CAM_PH_06": (13.0405, 80.1485),
    "CAM_PH_07": (13.0560, 80.1435), "CAM_PH_08": (13.0515, 80.1235),
    "CAM_PH_09": (13.0485, 80.1015), "CAM_PH_10": (13.0375, 80.0615),

    # CORRIDOR 6: ECR (East Coast Road)
    "CAM_EC_01": (12.9865, 80.2595), "CAM_EC_02": (12.9685, 80.2605),
    "CAM_EC_03": (12.9565, 80.2595), "CAM_EC_04": (12.9435, 80.2565),
    "CAM_EC_05": (12.9165, 80.2485), "CAM_EC_06": (12.8915, 80.2425),
    "CAM_EC_07": (12.8685, 80.2395), "CAM_EC_08": (12.8125, 80.2425),
    "CAM_EC_09": (12.7885, 80.2485), "CAM_EC_10": (12.6325, 80.1875),

    # CORRIDOR 7: Outer Ring Road (ORR)
    "CAM_OR_01": (13.1555, 80.1985), "CAM_OR_02": (13.0975, 80.1615),
    "CAM_OR_03": (13.1165, 80.1015), "CAM_OR_04": (13.1235, 80.0615),
    "CAM_OR_05": (13.0235, 80.0915), "CAM_OR_06": (12.9965, 80.0985),
    "CAM_OR_07": (12.9165, 80.0615), "CAM_OR_08": (12.8885, 80.0715),
    "CAM_OR_09": (13.2735, 80.2585), "CAM_OR_10": (13.1815, 80.2715),

    # CORRIDOR 8: South-East Hubs (Adyar, Mylapore, Marina)
    "CAM_SE_01": (13.0065, 80.2575), "CAM_SE_02": (12.9985, 80.2715),
    "CAM_SE_03": (13.0165, 80.2585), "CAM_SE_04": (13.0235, 80.2585),
    "CAM_SE_05": (13.0315, 80.2625), "CAM_SE_06": (13.0365, 80.2665),
    "CAM_SE_07": (13.0415, 80.2795), "CAM_SE_08": (13.0495, 80.2815),
    "CAM_SE_09": (13.0335, 80.2775), "CAM_SE_10": (13.0675, 80.2825),

    # CORRIDOR 9: North Chennai (Port & Commercial Routes)
    "CAM_NC_01": (13.1065, 80.2925), "CAM_NC_02": (13.1235, 80.2975),
    "CAM_NC_03": (13.1615, 80.3015), "CAM_NC_04": (13.2015, 80.3115),
    "CAM_NC_05": (13.1045, 80.2785), "CAM_NC_06": (13.1115, 80.2865),
    "CAM_NC_07": (13.1165, 80.2585), "CAM_NC_08": (13.0965, 80.2715),
    "CAM_NC_09": (13.1315, 80.2885), "CAM_NC_10": (13.0935, 80.2945),

    # CORRIDOR 10: Suburban Link Roads
    "CAM_SL_01": (12.9785, 80.2285), "CAM_SL_02": (12.9735, 80.2215),
    "CAM_SL_03": (12.9235, 80.1875), "CAM_SL_04": (12.9435, 80.2075),
    "CAM_SL_05": (12.9165, 80.1585), "CAM_SL_06": (12.9645, 80.1985),
    "CAM_SL_07": (12.9555, 80.1815), "CAM_SL_08": (13.0235, 80.1615),
    "CAM_SL_09": (13.0365, 80.1365), "CAM_SL_10": (12.9915, 80.0985),
}

ALL_CAMERAS = list(CAMERA_COORDINATES.keys())


# =============================================================================
# 3. SPATIAL GEODESIC UTILITIES & PROXIMITY GRAPH
# =============================================================================

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2.0) ** 2
    return r * (2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)))


calculate_haversine = haversine_km


def build_spatial_proximity_graph() -> Dict[str, List[str]]:
    """
    Constructs a physical proximity graph where edges ONLY exist between
    cameras that are physically adjacent (strictly within <= 3.5 km, average ~1.5 km).
    This strictly eliminates cross-city teleports and jumping over intermediate cameras.
    """
    graph: Dict[str, List[str]] = {}

    for c1, p1 in CAMERA_COORDINATES.items():
        candidates = []
        for c2, p2 in CAMERA_COORDINATES.items():
            if c1 == c2:
                continue
            dist = haversine_km(p1[0], p1[1], p2[0], p2[1])
            candidates.append((c2, dist))

        candidates.sort(key=lambda x: x[1])

        # Connect strictly to closest physical neighbors within 3.5 km ceiling
        close_neighbors = [c for c, d in candidates if d <= 3.5][:4]

        # Ensure isolated perimeter nodes have at least their closest neighbor
        if not close_neighbors and candidates:
            close_neighbors = [candidates[0][0]]

        graph[c1] = close_neighbors

    return graph


SPATIAL_PROXIMITY_GRAPH = build_spatial_proximity_graph()


# =============================================================================
# 4. GLOBALLY UNIQUE LICENSE PLATE REGISTRY
# =============================================================================

GENERATED_PLATES: Set[str] = set()
PLATE_LOCK = threading.Lock()

def generate_unique_plate() -> str:
    """Generates a globally unique Tamil Nadu registration plate with zero reuse."""
    districts = [
        "01", "02", "03", "04", "05", "06", "07", "09", "10", "11", "12",
        "14", "18", "19", "20", "21", "22", "23", "24", "25", "28", "38",
        "43", "45", "49", "51", "55", "57", "58", "60", "63", "65", "66",
        "67", "69", "70", "72", "74", "75", "76", "78", "81", "82", "83",
        "84", "85", "86", "87", "88", "90", "91", "92", "93", "94", "95"
    ]
    letters_pool = "ABCDEFGHJKLMNPQRSTUVWXYZ"

    with PLATE_LOCK:
        while True:
            dist = random.choice(districts)
            letters = random.choice(letters_pool) + random.choice(letters_pool)
            digits = f"{random.randint(1000, 9999)}"
            plate = f"TN{dist}{letters}{digits}"
            if plate not in GENERATED_PLATES:
                GENERATED_PLATES.add(plate)
                return plate


def weighted_vehicle_class() -> str:
    total = sum(w for _, w in VEHICLE_CLASSES)
    r = random.uniform(0, total)
    upto = 0
    for cls, weight in VEHICLE_CLASSES:
        if upto + weight >= r:
            return cls
        upto += weight
    return "SUV"


def generate_embedding() -> List[float]:
    vec = [random.uniform(-1, 1) for _ in range(3)]
    mag = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / mag, 4) for x in vec]


def calculate_segment_delay(cam_a: str, cam_b: Optional[str], vehicle_class: str) -> float:
    """
    Calculates physically realistic transit delay between consecutive adjacent cameras.
    """
    if not cam_b or cam_a == cam_b:
        return random.uniform(4.0, 7.0)

    pos_a = CAMERA_COORDINATES.get(cam_a, (13.0827, 80.2707))
    pos_b = CAMERA_COORDINATES.get(cam_b, (13.0827, 80.2707))
    dist_km = haversine_km(pos_a[0], pos_a[1], pos_b[0], pos_b[1])
    dist_km = max(0.4, dist_km)

    speed_map = {
        "Motorcycle": random.uniform(45, 60),
        "Hatchback": random.uniform(40, 55),
        "Sedan": random.uniform(45, 60),
        "SUV": random.uniform(45, 60),
        "Auto-Rickshaw": random.uniform(30, 42),
        "Commercial Truck": random.uniform(28, 38),
    }
    speed_kmh = speed_map.get(vehicle_class, 45.0)

    raw_transit_seconds = (dist_km / speed_kmh) * 3600.0
    # Scaled to live simulation pace (4 - 15 seconds per consecutive camera)
    sim_delay = max(4.0, min(16.0, raw_transit_seconds * 0.10 + random.uniform(1.0, 3.0)))
    return sim_delay


# =============================================================================
# 5. DIRECTIONAL MOMENTUM ROUTE GENERATOR (NO SKIPPING / NO SPIDERWEBS)
# =============================================================================

def generate_realistic_route(min_hops: int = 6, max_hops: int = 8) -> List[str]:
    """
    Generates a 100% physically realistic, step-by-step consecutive path
    using true GPS proximity and directional vector momentum.
    Every hop is strictly <= 3.0 km (average ~1.5 km), eliminating cross-city teleports.
    """
    for _ in range(80):
        start = random.choice(ALL_CAMERAS)
        candidates = []
        for c2 in ALL_CAMERAS:
            if start == c2:
                continue
            p1 = CAMERA_COORDINATES[start]
            p2 = CAMERA_COORDINATES[c2]
            d = haversine_km(p1[0], p1[1], p2[0], p2[1])
            if d <= 3.0:
                candidates.append((c2, d))

        if not candidates:
            continue

        candidates.sort(key=lambda x: x[1])
        second = random.choice(candidates[:3])[0]

        route = [start, second]
        visited = {start, second}

        for _ in range(max_hops - 2):
            curr = route[-1]
            prev = route[-2]
            p_prev = CAMERA_COORDINATES[prev]
            p_curr = CAMERA_COORDINATES[curr]

            v_dir = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
            mag_v = math.hypot(v_dir[0], v_dir[1])

            cands = []
            for nxt in ALL_CAMERAS:
                if nxt in visited:
                    continue
                p_nxt = CAMERA_COORDINATES[nxt]
                d = haversine_km(p_curr[0], p_curr[1], p_nxt[0], p_nxt[1])
                if d > 3.0:  # STRICT 3.0 KM HARD CEILING
                    continue

                v_nxt = (p_nxt[0] - p_curr[0], p_nxt[1] - p_curr[1])
                mag_nxt = math.hypot(v_nxt[0], v_nxt[1])
                if mag_nxt == 0 or mag_v == 0:
                    dot = 1.0
                else:
                    dot = (v_dir[0] * v_nxt[0] + v_dir[1] * v_nxt[1]) / (mag_v * mag_nxt)

                if dot > -0.2:
                    cands.append((nxt, dot, d))

            if not cands:
                break

            # Prioritize forward momentum and close distance
            cands.sort(key=lambda x: (-x[1], x[2]))
            chosen = cands[0][0]
            route.append(chosen)
            visited.add(chosen)

        if len(route) >= min_hops:
            return route

    # Fallback to nearest neighbor walk with <= 3.0 km constraint
    start = random.choice(ALL_CAMERAS)
    route = [start]
    visited = {start}
    curr = start
    while len(route) < min_hops:
        p_curr = CAMERA_COORDINATES[curr]
        neighbors = []
        for nxt in ALL_CAMERAS:
            if nxt in visited:
                continue
            p_nxt = CAMERA_COORDINATES[nxt]
            d = haversine_km(p_curr[0], p_curr[1], p_nxt[0], p_nxt[1])
            if d <= 3.0:
                neighbors.append((nxt, d))
        if not neighbors:
            break
        neighbors.sort(key=lambda x: x[1])
        nxt = neighbors[0][0]
        route.append(nxt)
        visited.add(nxt)
        curr = nxt

    return route


# =============================================================================
# 6. VEHICLE MODEL & FLEET MANAGEMENT
# =============================================================================

@dataclass
class Vehicle:
    plate: str
    route: List[str]
    vehicle_class: str
    vehicle_color: str
    step: int = 0
    next_detection_time: float = 0.0
    current_sim_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    embedding: List[float] = field(default_factory=list)
    is_watchlist: bool = False

    def current_camera(self) -> str:
        return self.route[self.step]

    def is_trip_completed(self) -> bool:
        return self.step >= len(self.route)


def create_vehicle(is_watchlist: bool = False, fixed_plate: Optional[str] = None) -> Vehicle:
    route = generate_realistic_route(min_hops=6, max_hops=8)
    v_class = weighted_vehicle_class()
    v_color = random.choice(VEHICLE_COLORS)
    plate = fixed_plate or generate_unique_plate()

    first_cam = route[0]
    next_cam = route[1] if len(route) > 1 else None
    initial_delay = calculate_segment_delay(first_cam, next_cam, v_class)

    return Vehicle(
        plate=plate,
        route=route,
        vehicle_class=v_class,
        vehicle_color=v_color,
        embedding=generate_embedding(),
        next_detection_time=time.time() + random.uniform(0.5, initial_delay),
        current_sim_time=datetime.now(timezone.utc),
        is_watchlist=is_watchlist
    )


# =============================================================================
# 7. HIGH-THROUGHPUT CONCURRENT EVENT PUBLISHER
# =============================================================================

class EventPublisher:
    def __init__(self, api_url: str, max_workers: int = 35):
        self.api_url = api_url
        self.session = requests.Session()

        adapter = HTTPAdapter(
            pool_connections=max_workers * 2,
            pool_maxsize=max_workers * 4,
            max_retries=Retry(total=1, backoff_factor=0.1)
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.sent_events = 0
        self.failed_events = 0
        self._lock = threading.Lock()

    def _send_request(self, payload: dict):
        try:
            res = self.session.post(self.api_url, json=payload, timeout=2.5)
            with self._lock:
                if res.status_code in (200, 201):
                    self.sent_events += 1
                else:
                    self.failed_events += 1
        except Exception:
            with self._lock:
                self.failed_events += 1

    def dispatch(self, vehicle: Vehicle, camera_id: str):
        payload = {
            "camera_id": camera_id,
            "plate_text": vehicle.plate,
            "ocr_confidence": round(random.uniform(0.92, 0.99), 2),
            "timestamp": vehicle.current_sim_time.isoformat(),
            "vehicle_class": vehicle.vehicle_class,
            "vehicle_color": vehicle.vehicle_color,
            "embedding": vehicle.embedding,
            "plate_crop_url": None
        }
        self.executor.submit(self._send_request, payload)

    def shutdown(self):
        self.executor.shutdown(wait=False)


# =============================================================================
# 8. TRAFFIC ENGINE & LIFECYCLE MANAGEMENT
# =============================================================================

class TrafficEngine:
    def __init__(self, target_vehicles: int):
        self.target_vehicles = target_vehicles
        self.publisher = EventPublisher(API_URL, max_workers=35)
        self.active_vehicles: List[Vehicle] = []
        self.watchlist_vehicles: List[Vehicle] = []
        self.lock = threading.Lock()
        self.running = True
        self._last_stats_time = time.time()
        self._last_sample_time = time.time()

    def spawn_vehicle(self):
        v = create_vehicle(is_watchlist=False)
        self.active_vehicles.append(v)

    def inject_vehicle(
        self,
        plate: str,
        route: Optional[List[str]] = None,
        vehicle_class: str = "SUV",
        vehicle_color: str = "Black",
        watchlist: bool = False
    ):
        if not route:
            route = generate_realistic_route(min_hops=6, max_hops=8)

        v = Vehicle(
            plate=plate,
            route=route,
            vehicle_class=vehicle_class,
            vehicle_color=vehicle_color,
            embedding=generate_embedding(),
            next_detection_time=time.time() + 1.0,
            current_sim_time=datetime.now(timezone.utc),
            is_watchlist=watchlist
        )

        with self.lock:
            self.active_vehicles.append(v)
            if watchlist:
                self.watchlist_vehicles.append(v)

        print(f"\n🚨 Injected {'WATCHLIST' if watchlist else 'Normal'} Target: {plate} -> Path: {' -> '.join(route)}")

    def maintain_population(self):
        """Continuously spawns fresh vehicles with globally unique plates to sustain target fleet."""
        current_count = len(self.active_vehicles)
        needed = self.target_vehicles - current_count
        if needed > 0:
            for _ in range(min(needed, 50)):
                self.spawn_vehicle()

    def process_vehicle(self, vehicle: Vehicle) -> bool:
        """
        Advances vehicle step-by-step to its physically adjacent camera node.
        Returns True if vehicle has completed its trip and should be permanently terminated.
        """
        now = time.time()
        if now < vehicle.next_detection_time:
            return False

        if vehicle.is_trip_completed():
            return True

        current_cam = vehicle.current_camera()
        self.publisher.dispatch(vehicle, current_cam)

        if vehicle.is_watchlist:
            utc_str = vehicle.current_sim_time.strftime("%H:%M:%S")
            print(f"🚨 WATCHLIST SIGHTING | {vehicle.plate} | {current_cam} | Step {vehicle.step + 1}/{len(vehicle.route)} | {utc_str} UTC")

        prev_cam = current_cam
        vehicle.step += 1

        # Check if vehicle has crossed its entire 6-8 node route
        if vehicle.is_trip_completed():
            return True

        next_cam = vehicle.current_camera()

        # 1. Calculate distance to the next camera
        prev_lat, prev_lon = CAMERA_COORDINATES[prev_cam]
        next_lat, next_lon = CAMERA_COORDINATES[next_cam]
        distance_km = calculate_haversine(prev_lat, prev_lon, next_lat, next_lon)

        # 2. Pick a realistic random cruise speed for this specific street segment (30 to 55 km/h)
        simulated_speed_kmh = random.uniform(30.0, 55.0)

        # 3. Calculate exact time it would take to drive that distance
        time_hours = distance_km / simulated_speed_kmh
        time_seconds = max(1, int(time_hours * 3600))

        # 4. Advance the simulated vehicle's clock by that exact realistic duration
        vehicle.current_sim_time += timedelta(seconds=time_seconds)

        # Wall-clock simulation pacing delay for the worker loop
        delay = calculate_segment_delay(prev_cam, next_cam, vehicle.vehicle_class)
        vehicle.next_detection_time = now + delay
        return False

    def simulation_tick(self):
        with self.lock:
            self.maintain_population()

            remaining_vehicles = []
            for v in self.active_vehicles:
                completed = self.process_vehicle(v)
                if not completed:
                    remaining_vehicles.append(v)
                else:
                    # Vehicle has crossed all 6-8 nodes: permanently terminate it and never reuse its plate
                    if v.is_watchlist:
                        print(f"🏁 WATCHLIST TARGET {v.plate} COMPLETED ROUTE ({len(v.route)} nodes) AND TERMINATED.")

            self.active_vehicles = remaining_vehicles

        now = time.time()
        if now - self._last_sample_time > 6.0:
            self.log_live_sample()
            self._last_sample_time = now

        if now - self._last_stats_time > 4.0:
            self.log_telemetry()
            self._last_stats_time = now

    def log_live_sample(self):
        if not self.active_vehicles:
            return
        sample = random.sample(self.active_vehicles, min(4, len(self.active_vehicles)))
        formatted = " | ".join(f"{v.plate}@{v.current_camera()} (step {v.step + 1}/{len(v.route)})" for v in sample)
        print(f"🧭 Grid Telemetry: {formatted}")

    def log_telemetry(self):
        sent = self.publisher.sent_events
        failed = self.publisher.failed_events
        active = len(self.active_vehicles)
        watch_count = len(self.watchlist_vehicles)
        total_unique = len(GENERATED_PLATES)
        print(f"🚗 Fleet: {active} Active | 📡 Sent: {sent} (Err: {failed}) | 🎯 Total Unique Vehicles: {total_unique} | 🚨 Tracked: {watch_count}")

    def stats(self) -> dict:
        return {
            "active_vehicles": len(self.active_vehicles),
            "events_posted": self.publisher.sent_events,
            "events_dropped": self.publisher.failed_events,
            "total_unique_plates": len(GENERATED_PLATES),
            "watchlist_targets": len(self.watchlist_vehicles)
        }

    def run(self):
        print("\n" + "=" * 65)
        print("🚦 CHENNAI CITY EYE - REALISTIC TRAFFIC SIMULATOR")
        print(f"🎯 Target Active Vehicles : {self.target_vehicles}")
        print(f"📡 Edge Ingestion API      : {API_URL}")
        print(f"🗺️  Spatial Graph Nodes    : {len(ALL_CAMERAS)} ANPR Cameras (Max Hop <= 3.2 km)")
        print("=" * 65 + "\n")

        while self.running:
            self.simulation_tick()
            time.sleep(TICK_RATE)

        self.publisher.shutdown()


# =============================================================================
# 9. INTERACTIVE COMMAND CONSOLE
# =============================================================================

class CommandConsole(threading.Thread):
    def __init__(self, engine: TrafficEngine):
        super().__init__(daemon=True)
        self.engine = engine

    def run(self):
        while True:
            try:
                cmd = input().strip()
                if not cmd:
                    continue

                parts = cmd.split()
                action = parts[0].lower()

                if action in ("inject", "watch"):
                    if len(parts) < 2:
                        print(f"Usage: {action} TN09AB9999")
                        continue
                    plate = parts[1].upper().strip()
                    self.engine.inject_vehicle(
                        plate=plate,
                        watchlist=(action == "watch")
                    )

                elif action == "traffic":
                    if len(parts) < 2:
                        print("Usage: traffic 1000")
                        continue
                    count = int(parts[1])
                    self.engine.target_vehicles = max(10, count)
                    print(f"🎯 Target active vehicles updated to: {self.engine.target_vehicles}")

                elif action == "stats":
                    print(self.engine.stats())

                elif action == "quit":
                    print("🛑 Stopping simulation engine...")
                    self.engine.running = False
                    break

                else:
                    print("\nCommands:")
                    print("  inject TN09AB1234   - Inject a normal vehicle")
                    print("  watch TN09AB9999    - Inject a blacklisted watchlist vehicle")
                    print("  traffic 1500        - Dynamically adjust target traffic density")
                    print("  stats               - Print current engine statistics")
                    print("  quit                - Terminate simulator\n")

            except Exception as e:
                print(f"Console Error: {e}")


# =============================================================================
# 10. CLI ENTRYPOINT
# =============================================================================

def resolve_vehicle_count(args) -> int:
    if args.traffic is not None:
        return max(10, args.traffic)

    if args.profile:
        return TRAFFIC_PROFILES.get(args.profile, 500)

    hour = datetime.now().hour
    if 7 <= hour <= 10 or 17 <= hour <= 21:
        return 1500
    elif 11 <= hour <= 16:
        return 700
    elif 22 <= hour <= 23:
        return 300
    return 150


def main():
    parser = argparse.ArgumentParser(description="Spatial Proximity Chennai Traffic Simulator for City EYE")
    parser.add_argument("--traffic", type=int, default=None, help="Target concurrent active vehicles")
    parser.add_argument("--profile", type=str, default=None, choices=list(TRAFFIC_PROFILES.keys()), help="Traffic load profile")
    args = parser.parse_args()

    target_fleet = resolve_vehicle_count(args)
    engine = TrafficEngine(target_vehicles=target_fleet)

    # Pre-inject demo watchlist vehicle
    engine.inject_vehicle(
        plate="TN09AB9999",
        vehicle_class="SUV",
        vehicle_color="Black",
        watchlist=True
    )

    console = CommandConsole(engine)
    console.start()

    try:
        engine.run()
    except KeyboardInterrupt:
        print("\n🛑 Simulator Stopped by User")


if __name__ == "__main__":
    main()