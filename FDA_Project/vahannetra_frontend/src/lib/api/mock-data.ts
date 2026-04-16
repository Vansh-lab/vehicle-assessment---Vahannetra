import type { AnalyticsPoint, FleetHealth, NotificationPreferences } from "@/lib/api/types";
import type { HistoryItem, InspectionResult } from "@/types/domain";

export const mockFleetHealth: FleetHealth = {
  score: 82,
  attentionVehicles: 14,
  inspectionsToday: 28,
  activeAlerts: 5,
};

export const mockRecentInspections: HistoryItem[] = [
  {
    id: "INSP-1021",
    plate: "MH12AB9087",
    model: "Hyundai i20",
    date: "2026-04-15T10:20:00Z",
    severity: "medium",
    status: "Completed",
    riskScore: 58,
  },
  {
    id: "INSP-1022",
    plate: "DL3CB7781",
    model: "Honda Activa",
    date: "2026-04-15T11:42:00Z",
    severity: "low",
    status: "Completed",
    riskScore: 31,
  },
  {
    id: "INSP-1023",
    plate: "KA05MN2211",
    model: "Tata Nexon",
    date: "2026-04-15T13:15:00Z",
    severity: "high",
    status: "Completed",
    riskScore: 84,
  },
];

export const mockAnalytics: AnalyticsPoint[] = [
  { month: "Jan", low: 28, medium: 14, high: 5 },
  { month: "Feb", low: 22, medium: 16, high: 6 },
  { month: "Mar", low: 30, medium: 18, high: 8 },
  { month: "Apr", low: 26, medium: 19, high: 7 },
  { month: "May", low: 33, medium: 15, high: 9 },
];

export const mockRiskRanking = [
  { model: "Mahindra Bolero", risk: 82 },
  { model: "Tata Ace", risk: 78 },
  { model: "Hyundai i20", risk: 61 },
  { model: "Maruti Swift", risk: 47 },
];

export const mockNotificationPrefs: NotificationPreferences = {
  push: true,
  email: true,
  criticalOnly: false,
};

export const mockInspectionResult: InspectionResult = {
  inspectionId: "INSP-VAH-2031",
  vehicle: {
    plate: "MH12AB9087",
    model: "Hyundai i20",
    vin: "MA3EHKD17A1234567",
    type: "4W",
    inspectedAt: "2026-04-16T13:10:00Z",
  },
  healthScore: 63,
  triageCategory: "STRUCTURAL/FUNCTIONAL",
  processedImageUrl: "/window.svg",
  findings: [
    {
      id: "DMG-1",
      type: "dent",
      severity: "high",
      confidence: 0.93,
      category: "Functional",
      estimateMin: 8500,
      estimateMax: 14000,
      explainability: "Panel deformation pattern and edge contour mismatch indicate a medium-to-high impact dent.",
      box: [40, 80, 210, 220],
    },
    {
      id: "DMG-2",
      type: "scratch",
      severity: "medium",
      confidence: 0.88,
      category: "Cosmetic",
      estimateMin: 2500,
      estimateMax: 4900,
      explainability: "Linear reflective discontinuity with paint-layer disruption resembles surface scratch clusters.",
      box: [250, 120, 390, 195],
    },
  ],
};
