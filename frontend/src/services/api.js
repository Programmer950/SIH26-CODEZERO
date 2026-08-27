/**
 * API Service Layer
 *
 * Currently returns mock data from src/data/.
 * When FastAPI backend is ready, replace mock imports with axios calls.
 *
 * CURRENT:  React → api.js → Mock Data (src/data/)
 * FUTURE:   React → api.js → FastAPI → AI / Database
 */

import axios from "axios";
import cameras from "../data/cameras";
import vehicles from "../data/vehicles";
import alerts from "../data/alerts";
import { hourlyTraffic, cameraTraffic, trafficZones, trafficStats } from "../data/traffic";

// Base URL for future FastAPI backend
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

// Axios instance — pre-configured for future use
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Fetch all cameras
 * Future: GET /api/cameras
 */
export const getCameras = async () => {
  // return (await apiClient.get("/cameras")).data;
  return cameras;
};

/**
 * Search for a vehicle by number plate
 * Future: GET /api/vehicles/search?number=TN09AB1234
 */
export const searchVehicle = async (vehicleNumber) => {
  // return (await apiClient.get(`/vehicles/search?number=${vehicleNumber}`)).data;
  const normalized = vehicleNumber.toUpperCase().replace(/\s/g, "");
  return vehicles.find((v) => v.number === normalized) || null;
};

/**
 * Fetch all vehicles
 * Future: GET /api/vehicles
 */
export const getVehicles = async () => {
  // return (await apiClient.get("/vehicles")).data;
  return vehicles;
};

/**
 * Fetch traffic data
 * Future: GET /api/traffic
 */
export const getTrafficData = async () => {
  // return (await apiClient.get("/traffic")).data;
  return {
    hourlyTraffic,
    cameraTraffic,
    trafficZones,
    trafficStats,
  };
};

/**
 * Fetch all alerts
 * Future: GET /api/alerts
 */
export const getAlerts = async () => {
  // return (await apiClient.get("/alerts")).data;
  return alerts;
};

export { apiClient };
