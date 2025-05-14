import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8000",
});

// Attach token automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("fraud_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
