// Mock camera data — replace with FastAPI responses via api.js
const cameras = [
  {
    id: "CAM01",
    name: "Anna Nagar Junction",
    latitude: 13.085,
    longitude: 80.21,
    status: "online",
    vehiclesDetected: 27,
    lastDetection: "13:48:21",
  },
  {
    id: "CAM02",
    name: "Adyar Signal",
    latitude: 13.0063,
    longitude: 80.2574,
    status: "online",
    vehiclesDetected: 34,
    lastDetection: "13:47:55",
  },
  {
    id: "CAM03",
    name: "Velachery Main Road",
    latitude: 12.9815,
    longitude: 80.2181,
    status: "offline",
    vehiclesDetected: 0,
    lastDetection: "13:44:12",
  },
  {
    id: "CAM05",
    name: "Guindy Junction",
    latitude: 13.006,
    longitude: 80.22,
    status: "online",
    vehiclesDetected: 41,
    lastDetection: "13:49:03",
  },
  {
    id: "CAM08",
    name: "Egmore Station",
    latitude: 13.0732,
    longitude: 80.2609,
    status: "online",
    vehiclesDetected: 19,
    lastDetection: "13:46:38",
  },
  {
    id: "CAM12",
    name: "T Nagar",
    latitude: 13.041,
    longitude: 80.234,
    status: "online",
    vehiclesDetected: 53,
    lastDetection: "13:49:11",
  },
];

export default cameras;
