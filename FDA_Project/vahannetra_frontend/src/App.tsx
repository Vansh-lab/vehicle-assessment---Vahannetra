import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { AppProviders } from "@/components/providers/app-providers";
import { AppShell } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/providers/auth-guard";

import LoginPage from "@/app/login/page";
import DashboardPage from "@/app/(workspace)/dashboard/page";
import NewInspectionPage from "@/app/(workspace)/inspection/new/page";
import ProcessingPage from "@/app/(workspace)/inspection/processing/page";
import ResultPage from "@/app/(workspace)/inspection/result/page";
import AdvancedInspectionPage from "@/app/(workspace)/inspection/advanced/page";
import HistoryPage from "@/app/(workspace)/history/page";
import HistoryDetailPage from "@/app/(workspace)/history/[id]/page";
import AnalyticsPage from "@/app/(workspace)/analytics/page";
import SettingsPage from "@/app/(workspace)/settings/page";

function WorkspaceLayout() {
  return (
    <AuthGuard>
      <AppShell>
        <Outlet />
      </AppShell>
    </AuthGuard>
  );
}

export default function App() {
  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-cyan-500 focus:px-3 focus:py-2 focus:text-slate-950"
      >
        Skip to main content
      </a>
      <AppProviders>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route element={<WorkspaceLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/inspection/new" element={<NewInspectionPage />} />
            <Route path="/inspection/processing" element={<ProcessingPage />} />
            <Route path="/inspection/result" element={<ResultPage />} />
            <Route path="/inspection/advanced" element={<AdvancedInspectionPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/history/:id" element={<HistoryDetailPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AppProviders>
    </>
  );
}
