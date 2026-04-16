import type { CaptureAngle, InspectionResult, VehicleType } from "@/types/domain";

export interface BackendAssessDamageResponse {
  inspection_summary: {
    dsi_score: number;
    overall_severity: "High" | "Moderate";
    triage_category: "COSMETIC" | "STRUCTURAL/FUNCTIONAL";
  };
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

export interface SettingsResponse {
  organization: {
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

export type ResultResponse = InspectionResult;
