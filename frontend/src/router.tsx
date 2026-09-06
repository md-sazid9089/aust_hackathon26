import { createBrowserRouter, Link, Navigate, RouterProvider, useRouteError } from 'react-router-dom';
import { FileQuestion } from 'lucide-react';
import { RequireAuth, RequireRole } from '@/auth/guards';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState, ErrorState } from '@/components/feedback/states';
import { Button } from '@/components/ui/button';
import { LoginPage } from '@/features/auth/LoginPage';
import { CoursesPage } from '@/features/courses/CoursesPage';
import { CoursePage } from '@/features/courses/CoursePage';
import { NewRunPage } from '@/features/runs/NewRunPage';
import { RunPage } from '@/features/runs/RunPage';
import { ComparePage } from '@/features/runs/ComparePage';
import { DashboardPage } from '@/features/dashboard/DashboardPage';
import { AdminDepartmentPage, AdminRunsPage, AdminSeedPage, AdminUsagePage, AdminUsersPage } from '@/features/admin/AdminPages';
import { MODULE_PATH } from '@/lib/format';
import type { RunModule } from '@/lib/types/api';

const MODULES = Object.keys(MODULE_PATH) as RunModule[];

function NotFound() {
  return (
    <EmptyState icon={FileQuestion} title="Page not found" description="The link may be outdated." action={<Button asChild><Link to="/">Back to start</Link></Button>} />
  );
}

function RouteError() {
  const err = useRouteError();
  return (
    <div className="p-8">
      <ErrorState error={err} onRetry={() => window.location.reload()} />
    </div>
  );
}

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage />, errorElement: <RouteError /> },
  {
    element: <RequireAuth />,
    errorElement: <RouteError />,
    children: [
      {
        element: <AppShell />,
        children: [
          // Run result pages are readable by both roles (admin read-only).
          ...MODULES.map((m) => ({ path: `/courses/:id/${MODULE_PATH[m]}/:runId`, element: <RunPage module={m} /> })),
          {
            element: <RequireRole role="faculty" />,
            children: [
              { path: '/', element: <CoursesPage /> },
              { path: '/dashboard', element: <DashboardPage /> },
              { path: '/courses/:id', element: <CoursePage /> },
              { path: '/courses/:id/exam-audit/compare', element: <ComparePage /> },
              ...MODULES.map((m) => ({ path: `/courses/:id/${MODULE_PATH[m]}/new`, element: <NewRunPage module={m} /> })),
            ],
          },
          {
            element: <RequireRole role="admin" />,
            children: [
              { path: '/admin', element: <AdminUsersPage /> },
              { path: '/admin/runs', element: <AdminRunsPage /> },
              { path: '/admin/usage', element: <AdminUsagePage /> },
              { path: '/admin/seed', element: <AdminSeedPage /> },
              { path: '/admin/department', element: <AdminDepartmentPage /> },
              { path: '/admin/users', element: <Navigate to="/admin" replace /> },
            ],
          },
          { path: '*', element: <NotFound /> },
        ],
      },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
