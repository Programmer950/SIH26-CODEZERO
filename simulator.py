import time
import math
import random
import threading
import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional

import requests


# =============================================================================
# CONFIG
# =============================================================================

API_URL = "http://localhost:8000/api/v1/events"

TICK_RATE = 1.0

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
# CAMERA CORRIDORS
# =============================================================================

ANNA_SALAI = [
    "CAM_AN_01",
    "CAM_AN_02",
    "CAM_AN_03",
    "CAM_AN_04",
    "CAM_AN_05",
    "CAM_AN_06",
    "CAM_AN_07",
    "CAM_AN_08",
    "CAM_AN_09",
    "CAM_AN_10",
]

OMR = [
    "CAM_OM_01",
    "CAM_OM_02",
    "CAM_OM_03",
    "CAM_OM_04",
    "CAM_OM_05",
    "CAM_OM_06",
    "CAM_OM_07",
    "CAM_OM_08",
    "CAM_OM_09",
    "CAM_OM_10",
]

GST = [
    "CAM_GS_01",
    "CAM_GS_02",
    "CAM_GS_03",
    "CAM_GS_04",
    "CAM_GS_05",
    "CAM_GS_06",
    "CAM_GS_07",
    "CAM_GS_08",
    "CAM_GS_09",
    "CAM_GS_10",
]

INNER_RING = [
    "CAM_IR_01",
    "CAM_IR_02",
    "CAM_IR_03",
    "CAM_IR_04",
    "CAM_IR_05",
    "CAM_IR_06",
    "CAM_IR_07",
    "CAM_IR_08",
    "CAM_IR_09",
    "CAM_IR_10",
]

POONAMALLEE = [
    "CAM_PH_01",
    "CAM_PH_02",
    "CAM_PH_03",
    "CAM_PH_04",
    "CAM_PH_05",
    "CAM_PH_06",
    "CAM_PH_07",
    "CAM_PH_08",
    "CAM_PH_09",
    "CAM_PH_10",
]

ECR = [
    "CAM_EC_01",
    "CAM_EC_02",
    "CAM_EC_03",
    "CAM_EC_04",
    "CAM_EC_05",
    "CAM_EC_06",
    "CAM_EC_07",
    "CAM_EC_08",
    "CAM_EC_09",
    "CAM_EC_10",
]

ORR = [
    "CAM_OR_01",
    "CAM_OR_02",
    "CAM_OR_03",
    "CAM_OR_04",
    "CAM_OR_05",
    "CAM_OR_06",
    "CAM_OR_07",
    "CAM_OR_08",
    "CAM_OR_09",
    "CAM_OR_10",
]

SOUTH_EAST = [
    "CAM_SE_01",
    "CAM_SE_02",
    "CAM_SE_03",
    "CAM_SE_04",
    "CAM_SE_05",
    "CAM_SE_06",
    "CAM_SE_07",
    "CAM_SE_08",
    "CAM_SE_09",
    "CAM_SE_10",
]

NORTH_CHENNAI = [
    "CAM_NC_01",
    "CAM_NC_02",
    "CAM_NC_03",
    "CAM_NC_04",
    "CAM_NC_05",
    "CAM_NC_06",
    "CAM_NC_07",
    "CAM_NC_08",
    "CAM_NC_09",
    "CAM_NC_10",
]

SUBURBAN = [
    "CAM_SL_01",
    "CAM_SL_02",
    "CAM_SL_03",
    "CAM_SL_04",
    "CAM_SL_05",
    "CAM_SL_06",
    "CAM_SL_07",
    "CAM_SL_08",
    "CAM_SL_09",
    "CAM_SL_10",
]

ALL_CORRIDORS = [
    ANNA_SALAI,
    OMR,
    GST,
    INNER_RING,
    POONAMALLEE,
    ECR,
    ORR,
    SOUTH_EAST,
    NORTH_CHENNAI,
    SUBURBAN,
]

CORRIDOR_TIMINGS = {
    "CAM_AN": (12, 35),
    "CAM_OM": (20, 60),
    "CAM_GS": (15, 45),
    "CAM_IR": (10, 25),
    "CAM_PH": (15, 40),
    "CAM_EC": (25, 75),
    "CAM_OR": (10, 30),
    "CAM_SE": (8, 20),
    "CAM_NC": (15, 40),
    "CAM_SL": (12, 35),
}


# =============================================================================
# VEHICLE MODEL
# =============================================================================

@dataclass
class Vehicle:
    plate: str
    route: List[str]

    vehicle_class: str
    vehicle_color: str

    step: int = 0

    next_detection: float = 0

    embedding: List[float] = field(default_factory=list)

    is_watchlist: bool = False

    def current_camera(self):
        return self.route[self.step]

    def finished(self):
        return self.step >= len(self.route)


# =============================================================================
# HELPERS
# =============================================================================

def generate_embedding():

    vec = [random.uniform(-1, 1) for _ in range(3)]

    mag = math.sqrt(sum(x * x for x in vec))

    return [round(x / mag, 4) for x in vec]


def generate_plate():

    districts = [
        "01",
        "02",
        "04",
        "07",
        "09",
        "10",
        "14",
        "18",
        "22",
    ]

    letters = "".join(
        random.choices(
            "ABCDEFGHJKLMNPQRSTUVWXYZ",
            k=2
        )
    )

    digits = random.randint(1000, 9999)

    return f"TN{random.choice(districts)}{letters}{digits}"


def weighted_vehicle_class():

    total = sum(w for _, w in VEHICLE_CLASSES)

    r = random.uniform(0, total)

    upto = 0

    for cls, weight in VEHICLE_CLASSES:

        if upto + weight >= r:
            return cls

        upto += weight

    return "SUV"

# =============================================================================
# ROUTE GENERATION
# =============================================================================

ALL_CAMERAS = [
    camera
    for corridor in ALL_CORRIDORS
    for camera in corridor
]


def corridor_for_camera(camera_id: str):

    for corridor in ALL_CORRIDORS:
        if camera_id in corridor:
            return corridor

    return random.choice(ALL_CORRIDORS)


def camera_distance(camera_a: str, camera_b: str):

    if camera_a == camera_b:
        return 0

    corridor_a = corridor_for_camera(camera_a)
    corridor_b = corridor_for_camera(camera_b)

    if corridor_a == corridor_b:
        return abs(
            corridor_a.index(camera_a) - corridor_a.index(camera_b)
        )

    return 5


def corridor_delay(camera_id: str, next_camera_id: Optional[str] = None):

    if next_camera_id is not None:
        distance = camera_distance(camera_id, next_camera_id)

        if distance == 0:
            return random.uniform(20, 35)

        base_seconds = 18 + distance * random.uniform(12, 18)
        return max(20, min(base_seconds, 180))

    for prefix, timing in CORRIDOR_TIMINGS.items():

        if camera_id.startswith(prefix):

            return random.uniform(*timing)

    return random.uniform(15, 40)


def build_route():

    """Keep vehicles moving through short, connected segments instead of teleporting across the city."""

    if random.random() < 0.82:

        corridor = random.choice(ALL_CORRIDORS)
        route_length = random.randint(3, min(6, len(corridor)))
        start = random.randint(0, max(0, len(corridor) - route_length))
        segment = corridor[start:start + route_length]

        if random.random() < 0.5:
            segment = list(reversed(segment))

        return segment

    c1 = random.choice(ALL_CORRIDORS)
    c2 = random.choice(ALL_CORRIDORS)

    while c2 == c1:
        c2 = random.choice(ALL_CORRIDORS)

    part1_len = random.randint(2, 4)
    part2_len = random.randint(2, 4)

    part1 = c1[max(0, len(c1) - part1_len):]
    part2 = c2[:part2_len]

    route = part1 + part2
    return route[:min(len(route), 8)]


def random_vehicle():

    route = build_route()

    return Vehicle(
        plate=generate_plate(),
        route=route,
        vehicle_class=weighted_vehicle_class(),
        vehicle_color=random.choice(VEHICLE_COLORS),
        embedding=generate_embedding(),
        next_detection=time.time() + random.uniform(25, 90)
    )


# =============================================================================
# EVENT POSTER
# =============================================================================

class EventPublisher:

    def __init__(self, api_url):

        self.api_url = api_url

        self.session = requests.Session()

        self.sent_events = 0

    def post(self, vehicle, camera_id):

        payload = {

            "camera_id": camera_id,

            "plate_text": vehicle.plate,

            "ocr_confidence": round(
                random.uniform(0.90, 0.99),
                2
            ),

            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "vehicle_class": vehicle.vehicle_class,

            "vehicle_color": vehicle.vehicle_color,

            "embedding": vehicle.embedding,

            "plate_crop_url": None
        }

        try:

            r = self.session.post(
                self.api_url,
                json=payload,
                timeout=3
            )

            self.sent_events += 1

            return r.status_code

        except Exception:

            return None


# =============================================================================
# TRAFFIC ENGINE
# =============================================================================

class TrafficEngine:

    def __init__(self, target_vehicles):

        self.target_vehicles = target_vehicles

        self.publisher = EventPublisher(API_URL)

        self.active_vehicles = []

        self.watchlist_vehicles = []

        self.lock = threading.Lock()

        self.running = True

        self._last_live_sample = 0.0

    # -------------------------------------------------------------------------
    # VEHICLE CREATION
    # -------------------------------------------------------------------------

    def spawn_vehicle(self):

        camera_counts = {
            camera: 0
            for camera in ALL_CAMERAS
        }

        for vehicle in self.active_vehicles:
            if not vehicle.finished():
                camera_counts[vehicle.current_camera()] = (
                    camera_counts.get(vehicle.current_camera(), 0) + 1
                )

        spawn_camera = min(
            ALL_CAMERAS,
            key=lambda camera: (camera_counts[camera], random.random())
        )

        corridor = corridor_for_camera(spawn_camera)
        idx = corridor.index(spawn_camera)

        remaining_after = max(1, len(corridor) - idx)
        max_route = min(6, remaining_after)
        min_route = 2 if max_route >= 2 else 1
        route_length = random.randint(min_route, max_route)

        start = max(0, idx - random.randint(0, min(2, idx)))
        end = min(len(corridor) - 1, start + route_length - 1)

        if end - start + 1 < route_length:
            start = max(0, end - route_length + 1)

        route = corridor[start:end + 1]

        if random.random() < 0.4:
            route = list(reversed(route))

        vehicle = Vehicle(
            plate=generate_plate(),
            route=route,
            vehicle_class=weighted_vehicle_class(),
            vehicle_color=random.choice(VEHICLE_COLORS),
            embedding=generate_embedding(),
            next_detection=time.time() + random.uniform(25, 90)
        )

        self.active_vehicles.append(vehicle)

    def inject_vehicle(
        self,
        plate,
        route=None,
        vehicle_class="SUV",
        vehicle_color="Black",
        watchlist=False
    ):

        if route is None:
            route = random.choice(ALL_CORRIDORS)

        v = Vehicle(
            plate=plate,
            route=route,
            vehicle_class=vehicle_class,
            vehicle_color=vehicle_color,
            embedding=generate_embedding(),
            next_detection=time.time() + random.uniform(20, 60),
            is_watchlist=watchlist
        )

        self.active_vehicles.append(v)

        if watchlist:
            self.watchlist_vehicles.append(v)

        print(
            f"\n🚨 Injected Vehicle: {plate}"
        )

    # -------------------------------------------------------------------------
    # SPAWNER
    # -------------------------------------------------------------------------

    def maintain_population(self):

        while len(self.active_vehicles) < self.target_vehicles:

            self.spawn_vehicle()

    # -------------------------------------------------------------------------
    # VEHICLE UPDATE
    # -------------------------------------------------------------------------

    def process_vehicle(self, vehicle):

        if time.time() < vehicle.next_detection:
            return

        if vehicle.finished():
            return

        camera_id = vehicle.current_camera()

        next_camera_id = None
        if vehicle.step + 1 < len(vehicle.route):
            next_camera_id = vehicle.route[vehicle.step + 1]

        status = self.publisher.post(
            vehicle,
            camera_id
        )

        if vehicle.is_watchlist:

            print(
                f"🚨 WATCHLIST | "
                f"{vehicle.plate} | "
                f"{camera_id} | "
                f"{status}"
            )

        vehicle.step += 1

        if vehicle.finished():

            try:
                self.active_vehicles.remove(vehicle)
            except ValueError:
                pass

            return

        vehicle.next_detection = (
            time.time()
            + corridor_delay(camera_id, next_camera_id)
        )

# =============================================================================
# CONGESTION MODEL
# =============================================================================

def congestion_multiplier(active_count):

    if active_count < 100:
        return 1.0

    if active_count < 300:
        return 1.2

    if active_count < 600:
        return 1.5

    if active_count < 1200:
        return 2.0

    return 3.0


# =============================================================================
# ENGINE LOOP
# =============================================================================

class TrafficEngine(TrafficEngine):

    def simulation_tick(self):

        self.maintain_population()

        active_snapshot = self.active_vehicles[:]

        for vehicle in active_snapshot:

            self.process_vehicle(vehicle)

        if time.time() - self._last_live_sample > 5:
            self.log_live_sample()
            self._last_live_sample = time.time()

        if random.random() < 0.02:

            self.spawn_vehicle()

    def log_live_sample(self):

        if not self.active_vehicles:
            return

        sample_count = min(5, len(self.active_vehicles))
        sample = random.sample(self.active_vehicles, sample_count)

        plates = " | ".join(
            f"{vehicle.plate}@{vehicle.current_camera()}"
            for vehicle in sample
        )

        print(f"\n🧭 Live sample: {plates}")

    def stats(self):

        return {
            "active": len(self.active_vehicles),
            "events": self.publisher.sent_events,
            "watchlist": len(self.watchlist_vehicles)
        }

    def run(self):

        print("\n🚦 Chennai Traffic Simulator Started")
        print(f"🎯 Target Vehicles: {self.target_vehicles}")
        print(f"📡 API: {API_URL}\n")

        last_stats = time.time()

        while self.running:

            self.simulation_tick()

            if time.time() - last_stats > 5:

                s = self.stats()

                print(
                    f"🚗 Active={s['active']} | "
                    f"📡 Events={s['events']} | "
                    f"🚨 Watchlist={s['watchlist']}"
                )

                last_stats = time.time()

            multiplier = congestion_multiplier(
                len(self.active_vehicles)
            )

            time.sleep(
                TICK_RATE * (1.0 / multiplier)
            )


# =============================================================================
# INTERACTIVE COMMAND THREAD
# =============================================================================

class CommandConsole(threading.Thread):

    def __init__(self, engine):

        super().__init__(daemon=True)

        self.engine = engine

    def run(self):

        while True:

            try:

                cmd = input().strip()

                if not cmd:
                    continue

                parts = cmd.split()

                if parts[0] == "inject":

                    if len(parts) < 2:

                        print(
                            "Usage: inject TN09AB9999"
                        )

                        continue

                    plate = parts[1]

                    route = random.choice(
                        ALL_CORRIDORS
                    )

                    self.engine.inject_vehicle(
                        plate=plate,
                        route=route,
                        vehicle_class="SUV",
                        vehicle_color="Black"
                    )

                elif parts[0] == "watch":

                    if len(parts) < 2:

                        print(
                            "Usage: watch TN09AB9999"
                        )

                        continue

                    plate = parts[1]

                    route = random.choice(
                        ALL_CORRIDORS
                    )

                    self.engine.inject_vehicle(
                        plate=plate,
                        route=route,
                        vehicle_class="SUV",
                        vehicle_color="Black",
                        watchlist=True
                    )

                elif parts[0] == "stats":

                    print(
                        self.engine.stats()
                    )

                elif parts[0] == "quit":

                    self.engine.running = False

                    break

                else:

                    print(
                        "\nCommands:"
                    )
                    print(
                        " inject TN09AB9999"
                    )
                    print(
                        " watch TN09AB9999"
                    )
                    print(
                        " stats"
                    )
                    print(
                        " quit\n"
                    )

            except Exception as e:

                print(
                    f"Console Error: {e}"
                )


# =============================================================================
# PROFILE RESOLUTION
# =============================================================================

def resolve_vehicle_count(args):

    if args.traffic is not None:

        return args.traffic

    if args.profile:

        return TRAFFIC_PROFILES.get(
            args.profile,
            500
        )

    hour = datetime.now().hour

    if 7 <= hour <= 10:

        return 1200

    if 17 <= hour <= 21:

        return 1800

    if 11 <= hour <= 16:

        return 700

    if 22 <= hour <= 23:

        return 300

    return 100


# =============================================================================
# MAIN
# =============================================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--traffic",
        type=int,
        default=None,
        help="Target active vehicles"
    )

    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        choices=list(
            TRAFFIC_PROFILES.keys()
        )
    )

    args = parser.parse_args()

    target = resolve_vehicle_count(
        args
    )

    engine = TrafficEngine(
        target_vehicles=target
    )

    # ---------------------------------------------------------------------
    # DEMO WATCHLIST VEHICLE
    # ---------------------------------------------------------------------

    engine.inject_vehicle(
        plate="TN09AB9999",
        route=ANNA_SALAI,
        vehicle_class="SUV",
        vehicle_color="Black",
        watchlist=True
    )

    # ---------------------------------------------------------------------
    # COMMAND CONSOLE
    # ---------------------------------------------------------------------

    console = CommandConsole(
        engine
    )

    console.start()

    try:

        engine.run()

    except KeyboardInterrupt:

        print(
            "\n🛑 Simulator Stopped"
        )


if __name__ == "__main__":

    main()