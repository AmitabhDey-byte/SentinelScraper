export type PricePoint = {
  observed_at: string;
  price: number | null;
};

export type Product = {
  id: number;
  collector_id: string;
  site_name: string;
  name: string;
  image_url: string | null;
  listing_url: string;
  price: number | null;
  stock_status: string | null;
  price_history: PricePoint[];
};

export type Incident = {
  id: number;
  collector_id: string;
  site_name: string;
  detected_at: string;
  dropped_fields: string[];
  recovered_fields: string[];
  rows_prev: number;
  rows_curr: number;
  healed_at: string | null;
  narration_text: string | null;
  narration_source: "gemini" | "fallback" | null;
  status: "open" | "healed";
};

export type Alert = {
  type: "price_drop" | "restock";
  product_id: number;
  collector_id: string;
  site_name: string;
  product_name: string;
  image_url: string | null;
  previous_value: number | null;
  current_value: number | null;
  delta: number | null;
  observed_at: string;
  stock_status: string | null;
};

export type CollectorStatus = {
  collector_id: string;
  site_name: string;
  category: string;
  status: "healthy" | "attention" | "failed" | "not_run";
  last_run_at: string | null;
  last_run_status: string | null;
  row_count: number | null;
  open_incidents: number;
};

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type ProductPage = Page<Product>;
export type AlertPage = Page<Alert>;
export type IncidentPage = Page<Incident>;

export type Profile = {
  user_id: string;
  favorites_count: number;
  auth_mode: "operator" | "local-demo";
};

export type MarketInsight = {
  headline: string;
  recommendation: string;
  rationale: string;
  confidence: "low" | "medium" | "high";
  source: "gemini" | "fallback";
};

export type OperationEvent = {
  at: string;
  message: string;
};

export type Operation = {
  id: string;
  kind: "scan" | "heal_proposal" | "approve_and_verify" | "auto_heal";
  status: "queued" | "running" | "completed" | "completed_with_errors" | "failed";
  incident_id: number | null;
  started_at: string;
  completed_at: string | null;
  events: OperationEvent[];
  error: string | null;
};
