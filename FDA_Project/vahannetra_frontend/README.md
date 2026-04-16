# Vahannetra AI Frontend

Premium, mobile-first UI for AI vehicle damage detection workflows.

## Tech Stack
- Next.js (App Router) + TypeScript
- Tailwind CSS
- React Query + Zustand
- React Hook Form + Zod
- Recharts
- Framer Motion
- shadcn-style reusable UI components

## Run
```bash
cd /home/runner/work/vehicle-assessment---Vahannetra/vehicle-assessment---Vahannetra/FDA_Project/vahannetra_frontend
npm install
npm run dev
```

Set env (optional):
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_USE_BACKEND=true
```

- `NEXT_PUBLIC_USE_BACKEND=true` enables real API call to `POST /assess-damage/`
- otherwise mock API data is used for prototype flow

## Information Architecture
- Auth
  - `/login`
- Workspace
  - `/dashboard`
  - `/inspection/new`
  - `/inspection/processing`
  - `/inspection/result`
  - `/history`
  - `/history/[id]`
  - `/analytics`
  - `/settings`

## User Flow (textual)
1. Login
2. Dashboard summary
3. Start inspection
4. Select vehicle type + details
5. Select angle coverage
6. Capture/upload image (camera/gallery/drag-drop)
7. AI processing stages (preprocess → detect → classify → severity)
8. Result report (annotated image, heatmap, confidence, cost, explainability)
9. Send to claim / download report
10. Review in history + analytics

## Component Hierarchy (high-level)
- `AppProviders`
  - `ThemeProvider`
  - `QueryClientProvider`
- `AppShell`
  - Sidebar + Mobile bottom nav
  - Screen pages
- Shared UI
  - `Button`, `Card`, `Input`, `Badge`, `Switch`, `Progress`, `Skeleton`
- Feature Components
  - `InspectionStepper`, `PhotoUpload`
  - `AnnotatedImageViewer`, `DamageCard`, `ConfidenceMeter`, `CostEstimateWidget`
  - `EmptyState`, `ErrorState`, `StatCard`

## Frontend Folder Structure
```txt
src/
  app/
    login/
    (workspace)/
      dashboard/
      inspection/new/
      inspection/processing/
      inspection/result/
      history/
      history/[id]/
      analytics/
      settings/
  components/
    providers/
    layout/
    ui/
    states/
    inspection/
    results/
    dashboard/
  lib/
    api/
      mock-responses/ai-results.json
    design-tokens.ts
    utils.ts
  store/
    inspection-store.ts
  types/
    domain.ts
```

## Reusable Components + Core Props
- `Button({ variant, size, ...props })`
- `Card({ className, ...props })`
- `Input({ ...props })`
- `Badge({ className, ...props })`
- `Progress({ value })`
- `Switch({ checked, onCheckedChange, label })`
- `InspectionStepper({ steps, activeStep })`
- `PhotoUpload({ file, onFileChange })`
- `AnnotatedImageViewer({ imageUrl, findings, heatmapEnabled })`
- `DamageCard({ finding })`
- `ConfidenceMeter({ confidence })`
- `CostEstimateWidget({ min, max })`
- `EmptyState({ title, description })`
- `ErrorState({ message, onRetry })`

## Backend Integration Status
### Already available in backend
- ✅ `POST /assess-damage/` (used in processing flow)
- ✅ `GET /view-result/{filename}` (processed image access)

### Missing backend modules (you can build)
- ❌ Auth endpoints
  - Build: `/auth/login`, `/auth/forgot-password`, `/auth/verify-otp`
  - Return JWT + refresh token + org-scoped user profile
- ❌ Dashboard overview
  - Build: `/dashboard/overview`
  - Return fleet score, recent inspections, attention list
- ❌ History + report endpoints
  - Build: `/inspections` (filters: vehicle/date/severity/status)
  - Build: `/inspections/{id}` + `/inspections/{id}/report.pdf`
- ❌ Analytics
  - Build: `/analytics/damage-distribution`
  - Build: `/analytics/severity-trends`
  - Build: `/analytics/vehicle-risk-ranking`
- ❌ Settings/Profile
  - Build: `/settings` GET/PATCH for org + notifications + theme

## Mock Responses
- Sample AI result JSON: `src/lib/api/mock-responses/ai-results.json`

## Production Polish Checklist
- [ ] Replace mock services with real endpoints
- [ ] Add auth token handling + refresh flow
- [ ] Add robust image quality checks (blur/brightness using CV pipeline)
- [ ] Add report PDF generation integration
- [ ] Add i18n + full accessibility audit (WCAG AA)
- [ ] Add telemetry + error monitoring (Sentry)
- [ ] Add E2E tests for inspection wizard and result report
- [ ] Harden security headers + CSP and upload validation
