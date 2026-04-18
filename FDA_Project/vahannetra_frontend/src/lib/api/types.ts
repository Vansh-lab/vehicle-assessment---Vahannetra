import type { CaptureAngle, InspectionResult, VehicleType } from "@/types/domain";

export interface BackendAssessDamageResponse {
  inspection_summary: {
    dsi_score: number;
    overall_severity: "High" | "Moderate";
    triage_category: "COSMETIC" | "STRUCTURAL/FUNCTIONAL";
  };
  inspection_id?: string;
  processed_image_url: string;
  findings: Array<{
    class: string;
    confidence: number;
    box: [number, number, number, number];
  }>;
}

export interface NewInspectionPayload {
  vehicleType: VehicleType;
  plate: string;
  model: string;
  vin?: string;
  angles: CaptureAngle[];
}

export interface AnalyticsPoint {
  month: string;
  low: number;
  medium: number;
  high: number;
}

export interface FleetHealth {
  score: number;
  attentionVehicles: number;
  inspectionsToday: number;
  activeAlerts: number;
}

export interface NotificationPreferences {
  push: boolean;
  email: boolean;
  criticalOnly: boolean;
}

export interface BackendCapability {
  key: string;
  status: "implemented" | "missing";
  endpoint?: string;
  howToBuild?: string;
}

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: string;
}

export interface AuthOrganization {
  id: string;
  name: string;
  region: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  issued_at: string;
  user: AuthUser;
  organization: AuthOrganization;
}

export interface ClaimSubmitResponse {
  claim_id: string;
  inspection_id: string;
  status: string;
  provider_reference: string;
}

export interface SettingsResponse {
  organization: {
    id?: string;
    name: string;
    region: string;
    active_inspectors: number;
  };
  notifications: {
    push: boolean;
    email: boolean;
    critical_only: boolean;
  };
  theme: "dark" | "light";
}

export interface VideoAnalyzeAccepted {
  job_id: string;
  status: string;
  message: string;
  estimated_seconds?: number;
}

export interface VideoResultPayload {
  job_id: string;
  status: string;
  input_type: string;
  dsq_score: number;
  overall_severity: "low" | "medium" | "high";
  confidence_overall: number;
  repair_cost_min_inr: number;
  repair_cost_max_inr: number;
  dsq_breakdown?: Record<string, number>;
}

export interface NearbyGarage {
  id: string;
  name: string;
  address: string;
  city?: string;
  phone?: string;
  latitude?: number;
  longitude?: number;
  distance_km: number;
  rating: number;
  is_open_now: boolean;
  smart_score: number;
  workshop_type?: string;
  services: string[];
  certifications?: string[];
  years_in_business?: number;
  hourly_labour_rate?: number;
  pricing: {
    scratch: { min: number; max: number };
    dent: { min: number; max: number };
    paint: { min: number; max: number };
    major: { min: number; max: number };
  };
  market_comparison?: Record<string, { market_avg: number; delta_pct: number; verdict: string }>;
  price_badge?: string;
  google_maps_url?: string;
}

export type ResultResponse = InspectionResult;
