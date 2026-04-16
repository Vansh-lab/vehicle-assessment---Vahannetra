import type {
  AnalyticsPoint,
  AuthResponse,
  BackendAssessDamageResponse,
  FleetHealth,
  NewInspectionPayload,
  NotificationPreferences,
  ResultResponse,
  SettingsResponse,
} from "@/lib/api/types";
import { API_BASE_URL, apiRequest } from "@/lib/api/client";
import {
  mockAnalytics,
  mockFleetHealth,
  mockInspectionResult,
  mockNotificationPrefs,
  mockRecentInspections,
  mockRiskRanking,
} from "@/lib/api/mock-data";
import { delay } from "@/lib/utils";
import type { HistoryItem } from "@/types/domain";

const USE_BACKEND = process.env.NEXT_PUBLIC_USE_BACKEND === "true";

function normalizeDetectionType(value: string): ResultResponse["findings"][number]["type"] {
  const normalized = value.toLowerCase();
  if (
    normalized === "scratch" ||
    normalized === "dent" ||
    normalized === "crack" ||
    normalized === "broken part" ||
    normalized === "paint damage"
  ) {
    return normalized;
  }
  return "paint damage";
}

function mapSeverityFromScore(score: number): "low" | "medium" | "high" {
  if (score > 70) return "high";
  if (score > 35) return "medium";
  return "low";
}

function mapHistoryItem(item: {
  id: string;
  plate: string;
  model: string;
  date: string;
  severity: "low" | "medium" | "high";
  status: "Completed" | "Pending" | "Failed";
  risk_score: number;
}): HistoryItem {
  return {
    id: item.id,
    plate: item.plate,
    model: item.model,
    date: item.date,
    severity: item.severity,
    status: item.status,
    riskScore: item.risk_score,
  };
}

export async function loginWithBackend(payload: {
  email: string;
  password: string;
  otp?: string;
}): Promise<AuthResponse> {
  if (!USE_BACKEND) {
    await delay(400);
    return {
      access_token: "mock-access",
      refresh_token: "mock-refresh",
      token_type: "bearer",
      expires_in: 3600,
      issued_at: new Date().toISOString(),
      user: {
        id: "usr_mock",
        name: "Demo Inspector",
        email: payload.email,
        role: "inspector",
      },
      organization: {
        id: "org_mock",
        name: "Acme Claims Pvt Ltd",
        region: "Mumbai",
      },
    };
  }

  return apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function assessDamageWithBackend(
  file: File,
  payload: NewInspectionPayload,
): Promise<ResultResponse> {
  if (!USE_BACKEND) return assessDamageMock(payload);

  const formData = new FormData();
  formData.append("file", file);

  const data = await apiRequest<BackendAssessDamageResponse>("/assess-damage/", {
    method: "POST",
    body: formData,
  });

  const severity = mapSeverityFromScore(data.inspection_summary.dsi_score);

  return {
    inspectionId: `INSP-${Date.now()}`,
    vehicle: {
      plate: payload.plate,
      model: payload.model,
      vin: payload.vin,
      type: payload.vehicleType,
      inspectedAt: new Date().toISOString(),
    },
    healthScore: Math.max(0, 100 - Math.round(data.inspection_summary.dsi_score)),
    triageCategory: data.inspection_summary.triage_category,
    processedImageUrl: `${API_BASE_URL}/${data.processed_image_url}`,
    findings: data.findings.map((item, index) => ({
      id: `DMG-${index + 1}`,
      type: normalizeDetectionType(item.class),
      severity,
      confidence: item.confidence,
      category: data.inspection_summary.triage_category === "COSMETIC" ? "Cosmetic" : "Functional",
      estimateMin: severity === "high" ? 8000 : severity === "medium" ? 3000 : 1200,
      estimateMax: severity === "high" ? 18000 : severity === "medium" ? 7000 : 2800,
      explainability: `Detected ${item.class} based on contour and texture anomalies from selected inspection angle(s).`,
      box: item.box,
    })),
  };
}

export async function assessDamageMock(payload: NewInspectionPayload): Promise<ResultResponse> {
  await delay(2200);
  return {
    ...mockInspectionResult,
    vehicle: {
      ...mockInspectionResult.vehicle,
      plate: payload.plate,
      model: payload.model,
      vin: payload.vin,
      type: payload.vehicleType,
      inspectedAt: new Date().toISOString(),
    },
  };
}

export async function getDashboardOverview(): Promise<{
  fleetHealth: FleetHealth;
  recentInspections: HistoryItem[];
}> {
  if (!USE_BACKEND) {
    await delay(500);
    return {
      fleetHealth: mockFleetHealth,
      recentInspections: mockRecentInspections,
    };
  }

  const data = await apiRequest<{
    fleet_health: {
      score: number;
      attention_vehicles: number;
      inspections_today: number;
      active_alerts: number;
    };
    recent_inspections: Array<{
      id: string;
      plate: string;
      model: string;
      date: string;
      severity: "low" | "medium" | "high";
      status: "Completed" | "Pending" | "Failed";
      risk_score: number;
    }>;
  }>("/dashboard/overview");

  return {
    fleetHealth: {
      score: data.fleet_health.score,
      attentionVehicles: data.fleet_health.attention_vehicles,
      inspectionsToday: data.fleet_health.inspections_today,
      activeAlerts: data.fleet_health.active_alerts,
    },
    recentInspections: data.recent_inspections.map(mapHistoryItem),
  };
}

export async function getFleetHealth(): Promise<FleetHealth> {
  const data = await getDashboardOverview();
  return data.fleetHealth;
}

export async function getRecentInspections(): Promise<HistoryItem[]> {
  const data = await getDashboardOverview();
  return data.recentInspections;
}

export async function getHistory(filters?: {
  search?: string;
  severity?: string;
  date?: string;
}): Promise<HistoryItem[]> {
  if (!USE_BACKEND) {
    await delay(700);
    return mockRecentInspections;
  }

  const params = new URLSearchParams();
  if (filters?.search) params.set("search", filters.search);
  if (filters?.severity && filters.severity !== "all") params.set("severity", filters.severity);
  if (filters?.date) params.set("date", filters.date);

  const query = params.toString();
  const path = query ? `/inspections?${query}` : "/inspections";

  const data = await apiRequest<
    Array<{
      id: string;
      plate: string;
      model: string;
      date: string;
      severity: "low" | "medium" | "high";
      status: "Completed" | "Pending" | "Failed";
      risk_score: number;
    }>
  >(path);

  return data.map(mapHistoryItem);
}

export async function getInspectionDetail(id: string): Promise<ResultResponse> {
  if (!USE_BACKEND) {
    await delay(300);
    return { ...mockInspectionResult, inspectionId: id };
  }

  const data = await apiRequest<{
    inspection_id: string;
    vehicle: {
      plate: string;
      model: string;
      vin?: string;
      type: "Motorcycle" | "Scooter" | "3W" | "4W";
      inspected_at: string;
    };
    health_score: number;
    triage_category: "COSMETIC" | "STRUCTURAL/FUNCTIONAL";
    processed_image_url: string;
    findings: Array<{
      id: string;
      type: "scratch" | "dent" | "crack" | "broken part" | "paint damage";
      severity: "low" | "medium" | "high";
      confidence: number;
      category: "Cosmetic" | "Functional";
      estimate_min: number;
      estimate_max: number;
      explainability: string;
      box: [number, number, number, number];
    }>;
  }>(`/inspections/${id}`);

  return {
    inspectionId: data.inspection_id,
    vehicle: {
      plate: data.vehicle.plate,
      model: data.vehicle.model,
      vin: data.vehicle.vin,
      type: data.vehicle.type,
      inspectedAt: data.vehicle.inspected_at,
    },
    healthScore: data.health_score,
    triageCategory: data.triage_category,
    processedImageUrl: `${API_BASE_URL}/${data.processed_image_url}`,
    findings: data.findings.map((item) => ({
      id: item.id,
      type: item.type,
      severity: item.severity,
      confidence: item.confidence,
      category: item.category,
      estimateMin: item.estimate_min,
      estimateMax: item.estimate_max,
      explainability: item.explainability,
      box: item.box,
    })),
  };
}

export function getInspectionReportUrl(id: string) {
  return `${API_BASE_URL}/inspections/${id}/report.pdf`;
}

export async function getAnalytics(): Promise<{
  trends: AnalyticsPoint[];
  riskRanking: { model: string; risk: number }[];
  distribution: { category: string; count: number }[];
}> {
  if (!USE_BACKEND) {
    await delay(700);
    return {
      trends: mockAnalytics,
      riskRanking: mockRiskRanking,
      distribution: [
        { category: "scratch", count: 12 },
        { category: "dent", count: 8 },
        { category: "crack", count: 3 },
        { category: "broken part", count: 2 },
        { category: "paint damage", count: 7 },
      ],
    };
  }

  const [trendsData, rankingData, distributionData] = await Promise.all([
    apiRequest<{ trends: AnalyticsPoint[] }>("/analytics/severity-trends"),
    apiRequest<{ ranking: { model: string; risk: number }[] }>("/analytics/vehicle-risk-ranking"),
    apiRequest<{ items: { category: string; count: number }[] }>("/analytics/damage-distribution"),
  ]);

  return {
    trends: trendsData.trends,
    riskRanking: rankingData.ranking,
    distribution: distributionData.items,
  };
}

export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  if (!USE_BACKEND) {
    await delay(400);
    return mockNotificationPrefs;
  }

  const data = await apiRequest<SettingsResponse>("/settings");
  return {
    push: data.notifications.push,
    email: data.notifications.email,
    criticalOnly: data.notifications.critical_only,
  };
}

export async function getSettings(): Promise<SettingsResponse> {
  if (!USE_BACKEND) {
    await delay(300);
    return {
      organization: {
        name: "Acme Claims Pvt Ltd",
        region: "Mumbai",
        active_inspectors: 42,
      },
      notifications: {
        push: mockNotificationPrefs.push,
        email: mockNotificationPrefs.email,
        critical_only: mockNotificationPrefs.criticalOnly,
      },
      theme: "dark",
    };
  }

  return apiRequest<SettingsResponse>("/settings");
}

export async function updateSettings(payload: {
  theme?: "dark" | "light";
  notifications?: NotificationPreferences;
}): Promise<SettingsResponse> {
  if (!USE_BACKEND) {
    await delay(200);
    const current = await getSettings();
    return {
      ...current,
      theme: payload.theme ?? current.theme,
      notifications: payload.notifications
        ? {
            push: payload.notifications.push,
            email: payload.notifications.email,
            critical_only: payload.notifications.criticalOnly,
          }
        : current.notifications,
    };
  }

  return apiRequest<SettingsResponse>("/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      theme: payload.theme,
      notifications: payload.notifications
        ? {
            push: payload.notifications.push,
            email: payload.notifications.email,
            critical_only: payload.notifications.criticalOnly,
          }
        : undefined,
    }),
  });
}
