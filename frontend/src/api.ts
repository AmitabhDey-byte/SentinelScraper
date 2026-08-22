import type {
  AlertPage,
  CollectorStatus,
  IncidentPage,
  MarketInsight,
  Operation,
  Product,
  ProductPage,
  Profile,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

let tokenGetter: (() => Promise<string | null>) | undefined;

export function configureApiAuth(getToken?: () => Promise<string | null>) {
  tokenGetter = getToken;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await tokenGetter?.();
  const headers = new Headers(init?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!token) headers.set("X-SentinelScrape-Demo-User", "local-observer");
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  return request<T>(path);
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
  profile: () => get<Profile>("/me/profile"),
  favorites: () => get<Product[]>("/me/favorites"),
  saveFavorite: (productId: number) =>
    request<Profile>(`/me/favorites/${productId}`, { method: "PUT" }),
  removeFavorite: (productId: number) =>
    request<Profile>(`/me/favorites/${productId}`, { method: "DELETE" }),
  marketInsight: () => get<MarketInsight>("/insights/market"),
  latestOperation: () => get<Operation | null>("/operations/latest"),
  operation: (operationId: string) => get<Operation>(`/operations/${operationId}`),
  scan: () => request<Operation>("/operations/scan", { method: "POST" }),
  proposeHeal: (incidentId: number) =>
    request<Operation>(`/operations/incidents/${incidentId}/heal`, { method: "POST" }),
  approveHeal: (incidentId: number) =>
    request<Operation>(`/operations/incidents/${incidentId}/approve`, { method: "POST" }),
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
