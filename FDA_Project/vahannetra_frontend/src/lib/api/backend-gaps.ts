import type { BackendCapability } from "@/lib/api/types";

export const backendCapabilities: BackendCapability[] = [
  {
    key: "AI damage assessment",
    status: "implemented",
    endpoint: "POST /assess-damage/",
  },
  {
    key: "Processed image fetch",
    status: "implemented",
    endpoint: "GET /view-result/{filename}",
  },
  {
    key: "Authentication",
    status: "implemented",
    endpoint: "POST /auth/login, POST /auth/forgot-password, POST /auth/verify-otp",
  },
  {
    key: "Fleet dashboard",
    status: "implemented",
    endpoint: "GET /dashboard/overview",
  },
  {
    key: "Inspection history and report PDF",
    status: "implemented",
    endpoint: "GET /inspections, GET /inspections/{id}, GET /inspections/{id}/report.pdf",
  },
  {
    key: "Analytics",
    status: "implemented",
    endpoint: "GET /analytics/damage-distribution, /analytics/severity-trends, /analytics/vehicle-risk-ranking",
  },
  {
    key: "Profile/settings",
    status: "implemented",
    endpoint: "GET /settings, PATCH /settings",
  },
  {
    key: "Claims integration",
    status: "implemented",
    endpoint: "POST /claims/submit",
  },
];
