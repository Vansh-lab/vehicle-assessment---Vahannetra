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
    status: "missing",
    howToBuild:
      "Create /auth/login, /auth/forgot-password, /auth/verify-otp with JWT + refresh token, and return user + org scope.",
  },
  {
    key: "Fleet dashboard",
    status: "missing",
    howToBuild:
      "Create /dashboard/overview endpoint returning fleet health score, recent inspections and attention vehicles.",
  },
  {
    key: "Inspection history and report PDF",
    status: "missing",
    howToBuild:
      "Create /inspections with search filters and /inspections/{id}/report.pdf endpoint.",
  },
  {
    key: "Analytics",
    status: "missing",
    howToBuild:
      "Create /analytics/damage-distribution, /analytics/severity-trends, /analytics/vehicle-risk-ranking endpoints.",
  },
  {
    key: "Profile/settings",
    status: "missing",
    howToBuild:
      "Create /settings GET/PATCH for organization profile, notifications, and theme preference.",
  },
];
