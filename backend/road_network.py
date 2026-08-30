"""
GIS Road Network Topology & Blind-Spot Interpolation Engine for Chennai Metropolitan Grid
Provides realistic curved road geometry waypoints, corridor transitions, and probabilistic routing.
"""

import math
from typing import List, Dict, Tuple, Optional
import networkx as nx

# Complete Camera Registry with Latitude, Longitude, Heading, Speed Limit
CAMERA_COORDINATES: Dict[str, Dict] = {
    # CORRIDOR 1: Anna Salai (Mount Road)
    'CAM_AN_01': {'name': 'Chennai Central Station Junction', 'lat': 13.0827, 'lon': 80.2707, 'corridor': 'ANNA_SALAI', 'speed_limit': 40},
    'CAM_AN_02': {'name': 'Pallavan Salai / Simpson', 'lat': 13.0722, 'lon': 80.2678, 'corridor': 'ANNA_SALAI', 'speed_limit': 40},
    'CAM_AN_03': {'name': 'LIC Building Junction', 'lat': 13.0645, 'lon': 80.2642, 'corridor': 'ANNA_SALAI', 'speed_limit': 40},
    'CAM_AN_04': {'name': 'Spencer Plaza Signal', 'lat': 13.0610, 'lon': 80.2605, 'corridor': 'ANNA_SALAI', 'speed_limit': 40},
    'CAM_AN_05': {'name': 'Gemini Flyover Underpass', 'lat': 13.0535, 'lon': 80.2504, 'corridor': 'ANNA_SALAI', 'speed_limit': 40},
    'CAM_AN_06': {'name': 'Teynampet Signal (DMS)', 'lat': 13.0416, 'lon': 80.2443, 'corridor': 'ANNA_SALAI', 'speed_limit': 40},
    'CAM_AN_07': {'name': 'Nandanam Signal', 'lat': 13.0315, 'lon': 80.2371, 'corridor': 'ANNA_SALAI', 'speed_limit': 40},
    'CAM_AN_08': {'name': 'Saidapet Panagal Maligai', 'lat': 13.0210, 'lon': 80.2265, 'corridor': 'ANNA_SALAI', 'speed_limit': 40},
    'CAM_AN_09': {'name': 'Little Mount Metro', 'lat': 13.0135, 'lon': 80.2198, 'corridor': 'ANNA_SALAI', 'speed_limit': 50},
    'CAM_AN_10': {'name': 'Guindy Kathipara Cloverleaf', 'lat': 13.0067, 'lon': 80.2025, 'corridor': 'ANNA_SALAI', 'speed_limit': 50},

    # CORRIDOR 2: OMR (Rajiv Gandhi Salai)
    'CAM_OM_01': {'name': 'Madhya Kailash Junction', 'lat': 13.0076, 'lon': 80.2449, 'corridor': 'OMR', 'speed_limit': 50},
    'CAM_OM_02': {'name': 'Tidel Park Signal', 'lat': 12.9895, 'lon': 80.2488, 'corridor': 'OMR', 'speed_limit': 50},
    'CAM_OM_03': {'name': 'SRP Tools Junction', 'lat': 12.9790, 'lon': 80.2483, 'corridor': 'OMR', 'speed_limit': 50},
    'CAM_OM_04': {'name': 'Perungudi Toll Plaza', 'lat': 12.9645, 'lon': 80.2445, 'corridor': 'OMR', 'speed_limit': 60},
    'CAM_OM_05': {'name': 'Thoraipakkam Radial Road Jn', 'lat': 12.9365, 'lon': 80.2315, 'corridor': 'OMR', 'speed_limit': 50},
    'CAM_OM_06': {'name': 'Karapakkam Signal', 'lat': 12.9165, 'lon': 80.2290, 'corridor': 'OMR', 'speed_limit': 50},
    'CAM_OM_07': {'name': 'Sholinganallur Junction', 'lat': 12.9015, 'lon': 80.2272, 'corridor': 'OMR', 'speed_limit': 50},
    'CAM_OM_08': {'name': 'Navalur Toll Plaza', 'lat': 12.8465, 'lon': 80.2245, 'corridor': 'OMR', 'speed_limit': 60},
    'CAM_OM_09': {'name': 'Siruseri SIPCOT Entrance', 'lat': 12.8280, 'lon': 80.2195, 'corridor': 'OMR', 'speed_limit': 50},
    'CAM_OM_10': {'name': 'Kelambakkam Junction', 'lat': 12.7915, 'lon': 80.2205, 'corridor': 'OMR', 'speed_limit': 50},

    # CORRIDOR 3: GST Road (Grand Southern Trunk)
    'CAM_GS_01': {'name': 'St Thomas Mount Station', 'lat': 12.9940, 'lon': 80.1945, 'corridor': 'GST', 'speed_limit': 50},
    'CAM_GS_02': {'name': 'Meenambakkam Airport Entry', 'lat': 12.9815, 'lon': 80.1765, 'corridor': 'GST', 'speed_limit': 50},
    'CAM_GS_03': {'name': 'Pallavaram Radial Road Jn', 'lat': 12.9675, 'lon': 80.1475, 'corridor': 'GST', 'speed_limit': 50},
    'CAM_GS_04': {'name': 'Chromepet MIT Gate', 'lat': 12.9515, 'lon': 80.1405, 'corridor': 'GST', 'speed_limit': 50},
    'CAM_GS_05': {'name': 'Tambaram Hindu Mission Jn', 'lat': 12.9245, 'lon': 80.1170, 'corridor': 'GST', 'speed_limit': 50},
    'CAM_GS_06': {'name': 'Perungalathur Bypass Entry', 'lat': 12.8985, 'lon': 80.0955, 'corridor': 'GST', 'speed_limit': 50},
    'CAM_GS_07': {'name': 'Vandalur Zoo Junction', 'lat': 12.8840, 'lon': 80.0825, 'corridor': 'GST', 'speed_limit': 50},
    'CAM_GS_08': {'name': 'Guduvanchery Signal', 'lat': 12.8445, 'lon': 80.0575, 'corridor': 'GST', 'speed_limit': 60},
    'CAM_GS_09': {'name': 'SRM University Potheri', 'lat': 12.8235, 'lon': 80.0440, 'corridor': 'GST', 'speed_limit': 60},
    'CAM_GS_10': {'name': 'Paranur Toll Plaza', 'lat': 12.7235, 'lon': 79.9925, 'corridor': 'GST', 'speed_limit': 80},

    # CORRIDOR 4: Inner Ring Road (100ft Road)
    'CAM_IR_01': {'name': 'Ashok Pillar Junction', 'lat': 13.0360, 'lon': 80.2115, 'corridor': 'INNER_RING', 'speed_limit': 50},
    'CAM_IR_02': {'name': 'Vadapalani Signal', 'lat': 13.0505, 'lon': 80.2118, 'corridor': 'INNER_RING', 'speed_limit': 40},
    'CAM_IR_03': {'name': 'Koyambedu Roundabout (CMBT)', 'lat': 13.0732, 'lon': 80.1937, 'corridor': 'INNER_RING', 'speed_limit': 50},
    'CAM_IR_04': {'name': 'Thirumangalam Junction', 'lat': 13.0845, 'lon': 80.1930, 'corridor': 'INNER_RING', 'speed_limit': 50},
    'CAM_IR_05': {'name': 'Anna Nagar Roundabout', 'lat': 13.0855, 'lon': 80.2115, 'corridor': 'INNER_RING', 'speed_limit': 40},
    'CAM_IR_06': {'name': 'Retteri Junction', 'lat': 13.1255, 'lon': 80.2135, 'corridor': 'INNER_RING', 'speed_limit': 50},
    'CAM_IR_07': {'name': 'Madhavaram Roundabout', 'lat': 13.1465, 'lon': 80.2335, 'corridor': 'INNER_RING', 'speed_limit': 50},
    'CAM_IR_08': {'name': 'Moolakadai Junction', 'lat': 13.1275, 'lon': 80.2445, 'corridor': 'INNER_RING', 'speed_limit': 50},
    'CAM_IR_09': {'name': 'Perambur Loco Works', 'lat': 13.1095, 'lon': 80.2375, 'corridor': 'INNER_RING', 'speed_limit': 40},
    'CAM_IR_10': {'name': 'Padi Flyover', 'lat': 13.0945, 'lon': 80.1870, 'corridor': 'INNER_RING', 'speed_limit': 50},

    # CORRIDOR 5: Poonamallee High Road
    'CAM_PH_01': {'name': 'Egmore Commissioner Office', 'lat': 13.0775, 'lon': 80.2625, 'corridor': 'POONAMALLEE', 'speed_limit': 40},
    'CAM_PH_02': {'name': 'Kilpauk Medical College', 'lat': 13.0785, 'lon': 80.2435, 'corridor': 'POONAMALLEE', 'speed_limit': 40},
    'CAM_PH_03': {'name': 'Aminjikarai Signal', 'lat': 13.0760, 'lon': 80.2235, 'corridor': 'POONAMALLEE', 'speed_limit': 40},
    'CAM_PH_04': {'name': 'Anna Arch Junction', 'lat': 13.0755, 'lon': 80.2155, 'corridor': 'POONAMALLEE', 'speed_limit': 40},
    'CAM_PH_05': {'name': 'Maduravoyal Bypass Junction', 'lat': 13.0645, 'lon': 80.1650, 'corridor': 'POONAMALLEE', 'speed_limit': 60},
    'CAM_PH_06': {'name': 'Porur Toll Plaza', 'lat': 13.0405, 'lon': 80.1485, 'corridor': 'POONAMALLEE', 'speed_limit': 60},
    'CAM_PH_07': {'name': 'Vanagaram Signal', 'lat': 13.0560, 'lon': 80.1435, 'corridor': 'POONAMALLEE', 'speed_limit': 50},
    'CAM_PH_08': {'name': 'Saveetha Dental College', 'lat': 13.0515, 'lon': 80.1235, 'corridor': 'POONAMALLEE', 'speed_limit': 50},
    'CAM_PH_09': {'name': 'Poonamallee Trunk Road', 'lat': 13.0485, 'lon': 80.1015, 'corridor': 'POONAMALLEE', 'speed_limit': 50},
    'CAM_PH_10': {'name': 'Nazarathpet Outer Ring', 'lat': 13.0375, 'lon': 80.0615, 'corridor': 'POONAMALLEE', 'speed_limit': 60},

    # CORRIDOR 6: ECR (East Coast Road)
    'CAM_EC_01': {'name': 'Thiruvanmiyur RTO', 'lat': 12.9865, 'lon': 80.2595, 'corridor': 'ECR', 'speed_limit': 50},
    'CAM_EC_02': {'name': 'Kottivakkam Signal', 'lat': 12.9685, 'lon': 80.2605, 'corridor': 'ECR', 'speed_limit': 50},
    'CAM_EC_03': {'name': 'Palavakkam Signal', 'lat': 12.9565, 'lon': 80.2595, 'corridor': 'ECR', 'speed_limit': 50},
    'CAM_EC_04': {'name': 'Neelankarai Junction', 'lat': 12.9435, 'lon': 80.2565, 'corridor': 'ECR', 'speed_limit': 50},
    'CAM_EC_05': {'name': 'Injambakkam ECR', 'lat': 12.9165, 'lon': 80.2485, 'corridor': 'ECR', 'speed_limit': 50},
    'CAM_EC_06': {'name': 'Akkarai Water Tank (ECR-OMR Link)', 'lat': 12.8915, 'lon': 80.2425, 'corridor': 'ECR', 'speed_limit': 50},
    'CAM_EC_07': {'name': 'Uthandi Toll Plaza', 'lat': 12.8685, 'lon': 80.2395, 'corridor': 'ECR', 'speed_limit': 60},
    'CAM_EC_08': {'name': 'Muttukadu Boat House', 'lat': 12.8125, 'lon': 80.2425, 'corridor': 'ECR', 'speed_limit': 60},
    'CAM_EC_09': {'name': 'Kovalam Junction', 'lat': 12.7885, 'lon': 80.2485, 'corridor': 'ECR', 'speed_limit': 60},
    'CAM_EC_10': {'name': 'Mahabalipuram Bypass', 'lat': 12.6325, 'lon': 80.1875, 'corridor': 'ECR', 'speed_limit': 60},

    # CORRIDOR 7: Chennai Outer Ring Road (ORR)
    'CAM_OR_01': {'name': 'Puzhal Toll Plaza', 'lat': 13.1555, 'lon': 80.1985, 'corridor': 'ORR', 'speed_limit': 80},
    'CAM_OR_02': {'name': 'Ambattur Industrial Estate', 'lat': 13.0975, 'lon': 80.1615, 'corridor': 'ORR', 'speed_limit': 60},
    'CAM_OR_03': {'name': 'Avadi Junction', 'lat': 13.1165, 'lon': 80.1015, 'corridor': 'ORR', 'speed_limit': 50},
    'CAM_OR_04': {'name': 'Pattabiram Signal', 'lat': 13.1235, 'lon': 80.0615, 'corridor': 'ORR', 'speed_limit': 50},
    'CAM_OR_05': {'name': 'Mangadu ORR Junction', 'lat': 13.0235, 'lon': 80.0915, 'corridor': 'ORR', 'speed_limit': 80},
    'CAM_OR_06': {'name': 'Kundrathur Bypass', 'lat': 12.9965, 'lon': 80.0985, 'corridor': 'ORR', 'speed_limit': 80},
    'CAM_OR_07': {'name': 'Mudichur ORR', 'lat': 12.9165, 'lon': 80.0615, 'corridor': 'ORR', 'speed_limit': 80},
    'CAM_OR_08': {'name': 'Vandalur ORR Toll', 'lat': 12.8885, 'lon': 80.0715, 'corridor': 'ORR', 'speed_limit': 80},
    'CAM_OR_09': {'name': 'Minjur Toll Plaza', 'lat': 13.2735, 'lon': 80.2585, 'corridor': 'ORR', 'speed_limit': 80},
    'CAM_OR_10': {'name': 'Manali Expressway', 'lat': 13.1815, 'lon': 80.2715, 'corridor': 'ORR', 'speed_limit': 60},

    # CORRIDOR 8: Adyar, Mylapore, Marina (South-East Hubs)
    'CAM_SE_01': {'name': 'Adyar Signal', 'lat': 13.0065, 'lon': 80.2575, 'corridor': 'SOUTH_EAST', 'speed_limit': 40},
    'CAM_SE_02': {'name': 'Besant Nagar Church', 'lat': 12.9985, 'lon': 80.2715, 'corridor': 'SOUTH_EAST', 'speed_limit': 40},
    'CAM_SE_03': {'name': 'Thiru Vi Ka Bridge', 'lat': 13.0165, 'lon': 80.2585, 'corridor': 'SOUTH_EAST', 'speed_limit': 50},
    'CAM_SE_04': {'name': 'Greenways Road MRTS', 'lat': 13.0235, 'lon': 80.2585, 'corridor': 'SOUTH_EAST', 'speed_limit': 40},
    'CAM_SE_05': {'name': 'Mandaveli Depot', 'lat': 13.0315, 'lon': 80.2625, 'corridor': 'SOUTH_EAST', 'speed_limit': 40},
    'CAM_SE_06': {'name': 'Mylapore Luz Corner', 'lat': 13.0365, 'lon': 80.2665, 'corridor': 'SOUTH_EAST', 'speed_limit': 40},
    'CAM_SE_07': {'name': 'Marina Beach Lighthouse', 'lat': 13.0415, 'lon': 80.2795, 'corridor': 'SOUTH_EAST', 'speed_limit': 40},
    'CAM_SE_08': {'name': 'Vivekanandar Illam', 'lat': 13.0495, 'lon': 80.2815, 'corridor': 'SOUTH_EAST', 'speed_limit': 40},
    'CAM_SE_09': {'name': 'Santhome Church', 'lat': 13.0335, 'lon': 80.2775, 'corridor': 'SOUTH_EAST', 'speed_limit': 40},
    'CAM_SE_10': {'name': 'Napier Bridge', 'lat': 13.0675, 'lon': 80.2825, 'corridor': 'SOUTH_EAST', 'speed_limit': 50},

    # CORRIDOR 9: North Chennai (Commercial & Port Routes)
    'CAM_NC_01': {'name': 'Royapuram Bridge', 'lat': 13.1065, 'lon': 80.2925, 'corridor': 'NORTH_CHENNAI', 'speed_limit': 40},
    'CAM_NC_02': {'name': 'Kasimedu Fishing Harbour', 'lat': 13.1235, 'lon': 80.2975, 'corridor': 'NORTH_CHENNAI', 'speed_limit': 40},
    'CAM_NC_03': {'name': 'Tiruvottiyur Theradi', 'lat': 13.1615, 'lon': 80.3015, 'corridor': 'NORTH_CHENNAI', 'speed_limit': 40},
    'CAM_NC_04': {'name': 'Ennore Port Road', 'lat': 13.2015, 'lon': 80.3115, 'corridor': 'NORTH_CHENNAI', 'speed_limit': 60},
    'CAM_NC_05': {'name': 'Mint Junction', 'lat': 13.1045, 'lon': 80.2785, 'corridor': 'NORTH_CHENNAI', 'speed_limit': 40},
    'CAM_NC_06': {'name': 'Washermanpet Metro', 'lat': 13.1115, 'lon': 80.2865, 'corridor': 'NORTH_CHENNAI', 'speed_limit': 40},
    'CAM_NC_07': {'name': 'Vyasarpadi Jeeva', 'lat': 13.1165, 'lon': 80.2585, 'corridor': 'NORTH_CHENNAI', 'speed_limit': 40},
    'CAM_NC_08': {'name': 'Basin Bridge', 'lat': 13.0965, 'lon': 80.2715, 'corridor': 'NORTH_CHENNAI', 'speed_limit': 40},
    'CAM_NC_09': {'name': 'Tondiarpet Signal', 'lat': 13.1315, 'lon': 80.2885, 'corridor': 'NORTH_CHENNAI', 'speed_limit': 40},
    'CAM_NC_10': {'name': 'Chennai Port Gate 1', 'lat': 13.0935, 'lon': 80.2945, 'corridor': 'NORTH_CHENNAI', 'speed_limit': 40},

    # CORRIDOR 10: Suburban Link Roads & Flyovers
    'CAM_SL_01': {'name': 'Tharamani Link Road', 'lat': 12.9785, 'lon': 80.2285, 'corridor': 'SUBURBAN', 'speed_limit': 50},
    'CAM_SL_02': {'name': 'Velachery Vijayanagar', 'lat': 12.9735, 'lon': 80.2215, 'corridor': 'SUBURBAN', 'speed_limit': 40},
    'CAM_SL_03': {'name': 'Medavakkam Junction', 'lat': 12.9235, 'lon': 80.1875, 'corridor': 'SUBURBAN', 'speed_limit': 50},
    'CAM_SL_04': {'name': 'Pallikaranai Marshland', 'lat': 12.9435, 'lon': 80.2075, 'corridor': 'SUBURBAN', 'speed_limit': 50},
    'CAM_SL_05': {'name': 'Kamarajapuram Signal', 'lat': 12.9165, 'lon': 80.1585, 'corridor': 'SUBURBAN', 'speed_limit': 40},
    'CAM_SL_06': {'name': 'Madipakkam Koot Road', 'lat': 12.9645, 'lon': 80.1985, 'corridor': 'SUBURBAN', 'speed_limit': 40},
    'CAM_SL_07': {'name': 'Keelkattalai Signal', 'lat': 12.9555, 'lon': 80.1815, 'corridor': 'SUBURBAN', 'speed_limit': 40},
    'CAM_SL_08': {'name': 'Mugalivakkam Signal', 'lat': 13.0235, 'lon': 80.1615, 'corridor': 'SUBURBAN', 'speed_limit': 40},
    'CAM_SL_09': {'name': 'Iyyappanthangal Depot', 'lat': 13.0365, 'lon': 80.1365, 'corridor': 'SUBURBAN', 'speed_limit': 40},
    'CAM_SL_10': {'name': 'Kundrathur Murugan Temple', 'lat': 12.9915, 'lon': 80.0985, 'corridor': 'SUBURBAN', 'speed_limit': 40}
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great circle distance in km."""
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def generate_curved_waypoints(p1: Tuple[float, float], p2: Tuple[float, float], num_midpoints: int = 3) -> List[List[float]]:
    """
    Generates realistic GIS curved road coordinates between two GPS points
    [lon, lat] adhering to urban road tortuosity instead of straight lines.
    """
    lon1, lat1 = p1
    lon2, lat2 = p2
    
    dist = haversine_km(lat1, lon1, lat2, lon2)
    if dist < 0.2:
        return [[lon1, lat1], [lon2, lat2]]

    waypoints = [[lon1, lat1]]
    
    # Perpendicular displacement factor to simulate natural road curvature
    d_lon = lon2 - lon1
    d_lat = lat2 - lat1
    perp_lon = -d_lat * 0.08
    perp_lat = d_lon * 0.08

    for i in range(1, num_midpoints + 1):
        t = i / (num_midpoints + 1)
        # S-curve / quadratic blend
        arc_offset = math.sin(t * math.pi)
        mid_lon = lon1 + t * d_lon + arc_offset * perp_lon
        mid_lat = lat1 + t * d_lat + arc_offset * perp_lat
        waypoints.append([round(mid_lon, 6), round(mid_lat, 6)])

    waypoints.append([lon2, lat2])
    return waypoints


class GISRoadNetworkGraph:
    """
    Spatial Road Network Topology Graph representing Chennai's arterial corridors,
    inter-corridor junction connectors, and blind-spot routing solvers.
    """
    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_network_topology()

    def _build_network_topology(self):
        # 1. Add all camera nodes with attributes
        for cam_id, meta in CAMERA_COORDINATES.items():
            self.graph.add_node(
                cam_id,
                name=meta['name'],
                lat=meta['lat'],
                lon=meta['lon'],
                corridor=meta['corridor'],
                speed_limit=meta['speed_limit']
            )

        # 2. Add sequential corridor edges (bi-directional arterial flow)
        corridors = {}
        for cam_id, meta in CAMERA_COORDINATES.items():
            corridors.setdefault(meta['corridor'], []).append(cam_id)

        for corridor_name, cam_list in corridors.items():
            for i in range(len(cam_list) - 1):
                u, v = cam_list[i], cam_list[i + 1]
                coord_u = (CAMERA_COORDINATES[u]['lon'], CAMERA_COORDINATES[u]['lat'])
                coord_v = (CAMERA_COORDINATES[v]['lon'], CAMERA_COORDINATES[v]['lat'])
                dist_km = haversine_km(coord_u[1], coord_u[0], coord_v[1], coord_v[0])
                road_dist_km = dist_km * 1.18  # Road tortuosity

                # Sequential corridor waypoints
                waypoints = generate_curved_waypoints(coord_u, coord_v, num_midpoints=2)

                self.graph.add_edge(u, v, weight=road_dist_km, distance_km=road_dist_km, waypoints=waypoints, corridor=corridor_name)
                self.graph.add_edge(v, u, weight=road_dist_km, distance_km=road_dist_km, waypoints=list(reversed(waypoints)), corridor=corridor_name)

        # 3. Add Key Inter-Corridor Arterial Connectors (Major City Flyovers & Junctions)
        connectors = [
            # Guindy Kathipara connects Anna Salai, GST, Inner Ring, and Suburban
            ('CAM_AN_10', 'CAM_GS_01', 'Kathipara Cloverleaf interchange to GST'),
            ('CAM_AN_10', 'CAM_IR_01', 'Kathipara to Ashok Pillar 100ft Road'),
            ('CAM_AN_10', 'CAM_SL_08', 'Kathipara to Mugalivakkam / Porur'),
            ('CAM_AN_09', 'CAM_OM_01', 'Little Mount to Madhya Kailash Link'),
            
            # Madhya Kailash connects Anna Salai / South East to OMR IT Expressway
            ('CAM_SE_01', 'CAM_OM_01', 'Adyar to Madhya Kailash OMR Gateway'),
            ('CAM_SE_01', 'CAM_EC_01', 'Adyar to Thiruvanmiyur ECR Gateway'),
            ('CAM_OM_01', 'CAM_SL_01', 'Madhya Kailash to Tharamani Link'),
            
            # Thoraipakkam Radial Road connects OMR & GST (Pallavaram)
            ('CAM_OM_05', 'CAM_GS_03', '200ft Thoraipakkam-Pallavaram Radial Road'),
            ('CAM_OM_05', 'CAM_SL_04', 'Thoraipakkam to Pallikaranai Marsh link'),
            ('CAM_SL_04', 'CAM_SL_02', 'Pallikaranai to Velachery Vijayanagar'),
            ('CAM_SL_02', 'CAM_OM_03', 'Velachery to SRP Tools OMR link'),
            
            # Akkarai Water Tank connects ECR to OMR Sholinganallur
            ('CAM_EC_06', 'CAM_OM_07', 'Kalaignar Karunanidhi ECR-OMR Link Road'),
            ('CAM_EC_01', 'CAM_OM_02', 'Thiruvanmiyur to Tidel Park'),
            
            # Koyambedu Junction connects Inner Ring Road & Poonamallee High Road
            ('CAM_IR_03', 'CAM_PH_04', 'Koyambedu Roundabout to Anna Arch Poonamallee High Rd'),
            ('CAM_IR_03', 'CAM_PH_05', 'Koyambedu to Maduravoyal Grade Separator'),
            ('CAM_PH_05', 'CAM_OR_05', 'Maduravoyal to Mangadu Outer Ring Road'),
            ('CAM_PH_06', 'CAM_SL_08', 'Porur Toll Plaza to Mugalivakkam link'),
            
            # Padi Flyover connects Inner Ring & Outer Ring / Ambattur
            ('CAM_IR_10', 'CAM_OR_02', 'Padi Flyover to Ambattur Industrial Estate'),
            ('CAM_IR_06', 'CAM_OR_01', 'Retteri Junction to Puzhal ORR Link'),
            ('CAM_IR_07', 'CAM_NC_07', 'Madhavaram to Vyasarpadi North Gateway'),
            
            # Gemini Flyover & City Center Connectors
            ('CAM_AN_05', 'CAM_SE_06', 'Gemini Flyover (Cathedral Rd) to Mylapore Luz'),
            ('CAM_AN_01', 'CAM_NC_08', 'Central Station to Basin Bridge North'),
            ('CAM_AN_01', 'CAM_PH_01', 'Central Station to Egmore Commissioner Office'),
            ('CAM_AN_01', 'CAM_SE_10', 'Central Station to Napier Bridge / Marina'),
            ('CAM_SE_10', 'CAM_SE_07', 'Napier Bridge to Marina Beach Lighthouse'),
            
            # Vandalur ORR connects GST and ORR
            ('CAM_GS_07', 'CAM_OR_08', 'Vandalur Zoo to Outer Ring Road Toll Interchange'),
            ('CAM_GS_06', 'CAM_OR_07', 'Perungalathur Bypass to Mudichur ORR'),
            ('CAM_SL_03', 'CAM_OM_07', 'Medavakkam Junction to Sholinganallur Link')
        ]

        for u, v, desc in connectors:
            if u in self.graph and v in self.graph:
                coord_u = (CAMERA_COORDINATES[u]['lon'], CAMERA_COORDINATES[u]['lat'])
                coord_v = (CAMERA_COORDINATES[v]['lon'], CAMERA_COORDINATES[v]['lat'])
                dist_km = haversine_km(coord_u[1], coord_u[0], coord_v[1], coord_v[0])
                road_dist_km = dist_km * 1.25  # Connector tortuosity

                waypoints = generate_curved_waypoints(coord_u, coord_v, num_midpoints=3)
                self.graph.add_edge(u, v, weight=road_dist_km, distance_km=road_dist_km, waypoints=waypoints, connector_name=desc)
                self.graph.add_edge(v, u, weight=road_dist_km, distance_km=road_dist_km, waypoints=list(reversed(waypoints)), connector_name=desc)

    def find_camera_node(self, camera_id: str) -> Optional[str]:
        """Finds closest node in graph or exact camera match."""
        if camera_id in self.graph:
            return camera_id
        # Fallback by substring matching
        for node in self.graph.nodes:
            if node in camera_id or camera_id in node:
                return node
        return None

    def interpolate_blind_spot(
        self,
        camera_a: str,
        camera_b: str,
        congestion_factors: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        Calculates the most probable GIS road path through an unmonitored blind zone
        between Camera A and Camera B using constrained graph shortest/probable path.
        """
        node_a = self.find_camera_node(camera_a)
        node_b = self.find_camera_node(camera_b)

        if not node_a or not node_b:
            return {
                "success": False,
                "is_blind_spot": False,
                "reason": "Camera not found in network topology",
                "coordinates": []
            }

        # If identical or directly adjacent on same corridor
        if node_a == node_b:
            coord = [CAMERA_COORDINATES[node_a]['lon'], CAMERA_COORDINATES[node_a]['lat']]
            return {
                "success": True,
                "is_blind_spot": False,
                "distance_km": 0.0,
                "coordinates": [coord],
                "path_nodes": [node_a]
            }

        # Dynamically calculate edge weights with traffic congestion penalties
        def edge_weight_func(u, v, data):
            base_dist = data.get('distance_km', 1.0)
            penalty = 1.0
            if congestion_factors:
                penalty = 1.0 + (congestion_factors.get(v, 0.0) * 0.5)
            return base_dist * penalty

        try:
            path_nodes = nx.shortest_path(self.graph, source=node_a, target=node_b, weight=edge_weight_func)
        except nx.NetworkXNoPath:
            # Fallback direct curved interpolation
            p1 = (CAMERA_COORDINATES[node_a]['lon'], CAMERA_COORDINATES[node_a]['lat'])
            p2 = (CAMERA_COORDINATES[node_b]['lon'], CAMERA_COORDINATES[node_b]['lat'])
            dist = haversine_km(p1[1], p1[0], p2[1], p2[0])
            waypoints = generate_curved_waypoints(p1, p2, num_midpoints=4)
            return {
                "success": True,
                "is_blind_spot": True,
                "gap_distance_km": round(dist, 2),
                "confidence": 0.65,
                "coordinates": waypoints,
                "path_nodes": [node_a, node_b],
                "via_corridors": [CAMERA_COORDINATES[node_a]['corridor'], CAMERA_COORDINATES[node_b]['corridor']]
            }

        # Stitch full multi-segment road geometry coordinates
        all_coordinates: List[List[float]] = []
        total_distance = 0.0
        corridors_traversed = []

        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            edge_data = self.graph.get_edge_data(u, v, default={})
            seg_dist = edge_data.get('distance_km', 1.0)
            total_distance += seg_dist
            
            c_u = CAMERA_COORDINATES[u]['corridor']
            if c_u not in corridors_traversed:
                corridors_traversed.append(c_u)

            seg_waypoints = edge_data.get('waypoints')
            if not seg_waypoints:
                p1 = (CAMERA_COORDINATES[u]['lon'], CAMERA_COORDINATES[u]['lat'])
                p2 = (CAMERA_COORDINATES[v]['lon'], CAMERA_COORDINATES[v]['lat'])
                seg_waypoints = generate_curved_waypoints(p1, p2, num_midpoints=2)

            if not all_coordinates:
                all_coordinates.extend(seg_waypoints)
            else:
                # Avoid duplicate stitch point
                all_coordinates.extend(seg_waypoints[1:])

        c_last = CAMERA_COORDINATES[path_nodes[-1]]['corridor']
        if c_last not in corridors_traversed:
            corridors_traversed.append(c_last)

        # Is considered a blind-spot gap if intermediate nodes were traversed
        is_blind_spot = len(path_nodes) > 2 or (
            CAMERA_COORDINATES[node_a]['corridor'] != CAMERA_COORDINATES[node_b]['corridor']
        )

        # Confidence decays gently with path length / blind zone size
        confidence = max(0.60, min(0.98, 1.0 - (len(path_nodes) - 2) * 0.06))

        return {
            "success": True,
            "is_blind_spot": is_blind_spot,
            "gap_distance_km": round(total_distance, 2),
            "confidence": round(confidence, 2),
            "coordinates": all_coordinates,
            "path_nodes": path_nodes,
            "via_corridors": corridors_traversed,
            "intermediate_count": max(0, len(path_nodes) - 2)
        }
