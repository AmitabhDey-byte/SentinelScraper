import type { Alert, CollectorStatus, Incident, Product } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  collectors: () => get<CollectorStatus[]>("/collectors"),
  products: () => get<Product[]>("/products"),
  incidents: () => get<Incident[]>("/incidents"),
  alerts: () => get<Alert[]>("/alerts"),
};
