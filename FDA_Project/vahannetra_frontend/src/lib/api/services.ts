import type {
  BackendAssessDamageResponse,
  FleetHealth,
  NewInspectionPayload,
  NotificationPreferences,
  ResultResponse,
  AnalyticsPoint,
} from "@/lib/api/types";
import { apiRequest, API_BASE_URL } from "@/lib/api/client";
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

export async function assessDamageWithBackend(
  file: File,
  payload: NewInspectionPayload,
): Promise<ResultResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const data = await apiRequest<BackendAssessDamageResponse>("/assess-damage/", {
    method: "POST",
    body: formData,
  });

  const severity = data.inspection_summary.dsi_score > 70 ? "high" : data.inspection_summary.dsi_score > 35 ? "medium" : "low";

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

export async function getFleetHealth(): Promise<FleetHealth> {
  await delay(500);
  return mockFleetHealth;
}

export async function getRecentInspections(): Promise<HistoryItem[]> {
  await delay(600);
  return mockRecentInspections;
}

export async function getHistory(): Promise<HistoryItem[]> {
  await delay(700);
  return mockRecentInspections;
}

export async function getAnalytics(): Promise<{ trends: AnalyticsPoint[]; riskRanking: { model: string; risk: number }[] }> {
  await delay(700);
  return {
    trends: mockAnalytics,
    riskRanking: mockRiskRanking,
  };
}

export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  await delay(400);
  return mockNotificationPrefs;
}
