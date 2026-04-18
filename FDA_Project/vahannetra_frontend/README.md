# Vahannetra AI Frontend

Premium, mobile-first UI for AI vehicle damage detection workflows.

## Tech Stack
- React + Vite + TypeScript
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
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_BACKEND=true
VITE_NOMINATIM_CONTACT_EMAIL=ops@example.com
```

- `VITE_USE_BACKEND=true` enables real API call to `POST /assess-damage/`
- otherwise mock API data is used for prototype flow
- `VITE_NOMINATIM_CONTACT_EMAIL` identifies your application for OSM Nominatim reverse-geocode usage

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
### Implemented backend modules
- ✅ `POST /assess-damage/`
- ✅ `GET /view-result/{filename}`
- ✅ `POST /auth/login`
- ✅ `POST /auth/forgot-password`
- ✅ `POST /auth/verify-otp`
- ✅ `POST /auth/refresh`
- ✅ `POST /auth/logout`
- ✅ `GET /dashboard/overview`
- ✅ `GET /inspections`
- ✅ `GET /inspections/{id}`
- ✅ `GET /inspections/{id}/report.pdf`
- ✅ `GET /analytics/damage-distribution`
- ✅ `GET /analytics/severity-trends`
- ✅ `GET /analytics/vehicle-risk-ranking`
- ✅ `GET /settings`
- ✅ `PATCH /settings`
- ✅ `POST /claims/submit`

### Still missing for full production backend
- ✅ OTP delivery retry telemetry persisted with callback endpoint support (`POST /auth/otp/delivery-callback`)
- ✅ Multi-tenant DB hardening hooks for PostgreSQL RLS policy setup + org session context (SQLite-safe fallback)
- ✅ Full timezone-aware datetime migration (`datetime.utcnow` deprecation cleanup)
- ✅ FastAPI startup lifecycle migrated from `on_event` to lifespan
- ✅ Secret manager abstraction with env/file/Vault lookup fallback

## Mock Responses
- Sample AI result JSON: `src/lib/api/mock-responses/ai-results.json`

## Production Polish Checklist
- [x] Replace mock services with real endpoints
- [x] Add auth token handling + refresh flow
- [x] Add robust image quality checks (blur/brightness using CV pipeline)
- [x] Add report PDF generation integration
- [x] Add i18n foundation + accessibility improvements (language selector + skip link)
- [x] Add telemetry + client error monitoring endpoint wiring
- [x] Add E2E tests for inspection wizard and result report flow
- [x] Harden security headers + CSP and upload validation
