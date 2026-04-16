export type VehicleType = "Motorcycle" | "Scooter" | "3W" | "4W";
export type CaptureAngle =
  | "Front"
  | "Rear"
  | "Left"
  | "Right"
  | "Top"
  | "Interior"
  | "Engine";

export type SeverityLevel = "low" | "medium" | "high";

export interface VehicleSummary {
  plate: string;
  model: string;
  vin?: string;
  type: VehicleType;
  inspectedAt: string;
}

export interface DamageFinding {
  id: string;
  type: "scratch" | "dent" | "crack" | "broken part" | "paint damage";
  severity: SeverityLevel;
  confidence: number;
  category: "Cosmetic" | "Functional";
  estimateMin: number;
  estimateMax: number;
  explainability: string;
  box: [number, number, number, number];
}

export interface InspectionResult {
  inspectionId: string;
  vehicle: VehicleSummary;
  healthScore: number;
  triageCategory: "COSMETIC" | "STRUCTURAL/FUNCTIONAL";
  processedImageUrl: string;
  findings: DamageFinding[];
}

export interface HistoryItem {
  id: string;
  plate: string;
  model: string;
  date: string;
  severity: SeverityLevel;
  status: "Completed" | "Pending" | "Failed";
  riskScore: number;
}
