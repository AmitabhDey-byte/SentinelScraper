import type {
  AlertPage,
  CollectorStatus,
  IncidentPage,
  ProductPage,
} from "./types";

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
  products: (
    params: {
      page?: number;
      pageSize?: number;
      site?: string;
      q?: string;
    } = {},
  ) => get<ProductPage>(buildQuery("/products", params)),
  incidents: (params: { page?: number; pageSize?: number } = {}) =>
    get<IncidentPage>(buildQuery("/incidents", params)),
  alerts: (params: { page?: number; pageSize?: number } = {}) =>
    get<AlertPage>(buildQuery("/alerts", params)),
};

function buildQuery(
  path: string,
  params: Record<string, string | number | undefined>,
) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      query.set(key.replace("pageSize", "page_size"), String(value));
    }
  }
  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
}
