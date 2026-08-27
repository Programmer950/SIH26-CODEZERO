// Mock vehicle data — replace with FastAPI responses via api.js
const vehicles = [
  {
    number: "TN09AB1234",
    type: "Sedan",
    color: "White",
    status: "normal",
    detections: [
      {
        cameraId: "CAM01",
        location: "Anna Nagar Junction",
        timestamp: "13:21:03",
        latitude: 13.085,
        longitude: 80.21,
        confidence: 98.4,
      },
      {
        cameraId: "CAM05",
        location: "Guindy Junction",
        timestamp: "13:27:42",
        latitude: 13.006,
        longitude: 80.22,
        confidence: 97.8,
      },
      {
        cameraId: "CAM12",
        location: "T Nagar",
        timestamp: "13:38:51",
        latitude: 13.041,
        longitude: 80.234,
        confidence: 99.1,
      },
    ],
  },
  {
    number: "TN09XY7788",
    type: "SUV",
    color: "Black",
    status: "blacklisted",
    detections: [
      {
        cameraId: "CAM02",
        location: "Adyar Signal",
        timestamp: "13:30:14",
        latitude: 13.0063,
        longitude: 80.2574,
        confidence: 96.2,
      },
      {
        cameraId: "CAM05",
        location: "Guindy Junction",
        timestamp: "13:42:18",
        latitude: 13.006,
        longitude: 80.22,
        confidence: 98.7,
      },
    ],
  },
  {
    number: "TN10AB1234",
    type: "Hatchback",
    color: "Silver",
    status: "watchlist",
    detections: [
      {
        cameraId: "CAM08",
        location: "Egmore Station",
        timestamp: "13:15:47",
        latitude: 13.0732,
        longitude: 80.2609,
        confidence: 95.3,
      },
      {
        cameraId: "CAM12",
        location: "T Nagar",
        timestamp: "13:36:21",
        latitude: 13.041,
        longitude: 80.234,
        confidence: 97.1,
      },
      {
        cameraId: "CAM01",
        location: "Anna Nagar Junction",
        timestamp: "13:52:09",
        latitude: 13.085,
        longitude: 80.21,
        confidence: 96.8,
      },
    ],
  },
];

export default vehicles;
