// Mock traffic data — replace with FastAPI responses via api.js

// Hourly vehicle detection data for the line chart
export const hourlyTraffic = [
  { hour: "06:00", vehicles: 320 },
  { hour: "07:00", vehicles: 780 },
  { hour: "08:00", vehicles: 1450 },
  { hour: "09:00", vehicles: 1820 },
  { hour: "10:00", vehicles: 1340 },
  { hour: "11:00", vehicles: 980 },
  { hour: "12:00", vehicles: 1120 },
  { hour: "13:00", vehicles: 1560 },
  { hour: "14:00", vehicles: 1290 },
  { hour: "15:00", vehicles: 1050 },
  { hour: "16:00", vehicles: 890 },
  { hour: "17:00", vehicles: 1680 },
  { hour: "18:00", vehicles: 1920 },
  { hour: "19:00", vehicles: 1540 },
  { hour: "20:00", vehicles: 870 },
  { hour: "21:00", vehicles: 520 },
];

// Vehicle count per camera for bar chart
export const cameraTraffic = [
  { camera: "CAM01", vehicles: 1842, name: "Anna Nagar" },
  { camera: "CAM02", vehicles: 1567, name: "Adyar" },
  { camera: "CAM03", vehicles: 0, name: "Velachery" },
  { camera: "CAM05", vehicles: 2134, name: "Guindy" },
  { camera: "CAM08", vehicles: 1203, name: "Egmore" },
  { camera: "CAM12", vehicles: 2890, name: "T Nagar" },
];

// Traffic density zones for map visualization
export const trafficZones = [
  {
    id: "TZ01",
    name: "Anna Nagar Junction",
    latitude: 13.085,
    longitude: 80.21,
    density: "high",
    vehicleCount: 1842,
    radius: 500,
  },
  {
    id: "TZ02",
    name: "Adyar Signal",
    latitude: 13.0063,
    longitude: 80.2574,
    density: "medium",
    vehicleCount: 1567,
    radius: 400,
  },
  {
    id: "TZ03",
    name: "Velachery Main Road",
    latitude: 12.9815,
    longitude: 80.2181,
    density: "low",
    vehicleCount: 0,
    radius: 300,
  },
  {
    id: "TZ04",
    name: "Guindy Junction",
    latitude: 13.006,
    longitude: 80.22,
    density: "very-high",
    vehicleCount: 2134,
    radius: 600,
  },
  {
    id: "TZ05",
    name: "Egmore Station",
    latitude: 13.0732,
    longitude: 80.2609,
    density: "medium",
    vehicleCount: 1203,
    radius: 400,
  },
  {
    id: "TZ06",
    name: "T Nagar",
    latitude: 13.041,
    longitude: 80.234,
    density: "very-high",
    vehicleCount: 2890,
    radius: 650,
  },
  {
    id: "TZ07",
    name: "Mylapore Temple",
    latitude: 13.0339,
    longitude: 80.2695,
    density: "high",
    vehicleCount: 1720,
    radius: 450,
  },
];

// Traffic statistics
export const trafficStats = {
  peakZone: "T Nagar",
  totalVehicles: 12842,
  activeCameras: 24,
  highDensityCameras: 7,
};
