import axios from "axios";

// In sviluppo il proxy di Vite gestisce /api -> localhost:8000; in produzione
// (Docker) e' nginx a instradare /api verso il container backend.
const baseURL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export const api = axios.create({ baseURL });

export const PropertiesAPI = {
  list: (params) => api.get("/properties", { params }).then((r) => r.data),
  get: (id) => api.get(`/properties/${id}`).then((r) => r.data),
};

export const ReviewsAPI = {
  list: (propertyId, limit = 50) =>
    api.get("/reviews", { params: { property_id: propertyId, limit } }).then((r) => r.data),
};

export const AnalyticsAPI = {
  forProperty: (propertyId) => api.get(`/analytics/properties/${propertyId}`).then((r) => r.data),
};

export const AiAPI = {
  summary: (propertyId) => api.post("/ai/summary", { property_id: propertyId }).then((r) => r.data),
  comparison: (propertyIds) =>
    api.post("/ai/comparison", { property_ids: propertyIds }).then((r) => r.data),
  suggestions: (propertyId) =>
    api.post("/ai/suggestions", { property_id: propertyId }).then((r) => r.data),
  // Report AI gia' generati (piu' recente per primo), per ripresentarli senza
  // doverli rigenerare a ogni apertura della pagina.
  reports: (params) => api.get("/ai/reports", { params }).then((r) => r.data),
};

export const IngestionAPI = {
  seedDemoData: () => api.post("/ingestion/seed-demo-data").then((r) => r.data),
  run: (payload) => api.post("/ingestion/run", payload).then((r) => r.data),
};
