import { lazy, Suspense, type ComponentType } from 'react';
import { createBrowserRouter, Link, Navigate, RouterProvider, useRouteError } from 'react-router-dom';
import { FileQuestion, Loader2 } from 'lucide-react';
import { RequireAuth, RequireRole } from '@/auth/guards';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState, ErrorState } from '@/components/feedback/states';
import { Button } from '@/components/ui/button';
import { LoginPage } from '@/features/auth/LoginPage';
import { CoursesPage } from '@/features/courses/CoursesPage';
import { MODULE_PATH } from '@/lib/format';
import type { RunModule } from '@/lib/types/api';

// Route-level code splitting: only login + course list ship in the initial bundle.
const LandingPage = lazy(() => import('@/features/landing/LandingPage'));
const CoursePage = lazy(() => import('@/features/courses/CoursePage').then((m) => ({ default: m.CoursePage })));
const NewRunPage = lazy(() => import('@/features/runs/NewRunPage').then((m) => ({ default: m.NewRunPage })));
const RunPage = lazy(() => import('@/features/runs/RunPage').then((m) => ({ default: m.RunPage })));
const ComparePage = lazy(() => import('@/features/runs/ComparePage').then((m) => ({ default: m.ComparePage })));
const DashboardPage = lazy(() => import('@/features/dashboard/DashboardPage').then((m) => ({ default: m.DashboardPage })));
const adminPages = () => import('@/features/admin/AdminPages');
const AdminUsersPage = lazy(() => adminPages().then((m) => ({ default: m.AdminUsersPage })));
const AdminRunsPage = lazy(() => adminPages().then((m) => ({ default: m.AdminRunsPage })));
const AdminUsagePage = lazy(() => adminPages().then((m) => ({ default: m.AdminUsagePage })));
const AdminSeedPage = lazy(() => adminPages().then((m) => ({ default: m.AdminSeedPage })));
const AdminDepartmentPage = lazy(() => adminPages().then((m) => ({ default: m.AdminDepartmentPage })));

function PageFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-muted-foreground" role="status" aria-live="polite">
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
      <span className="sr-only">Loading</span>
    </div>
  );
}

function page<P extends object>(Comp: ComponentType<P>, props?: P) {
  return (
    <Suspense fallback={<PageFallback />}>
      <Comp {...(props as P)} />
    </Suspense>
  );
}

const MODULES = Object.keys(MODULE_PATH) as RunModule[];

function NotFound() {
  return (
    <EmptyState icon={FileQuestion} title="Page not found" description="The link may be outdated." action={<Button asChild><Link to="/courses">Back to start</Link></Button>} />
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
  { path: '/', element: page(LandingPage), errorElement: <RouteError /> },
  { path: '/login', element: <LoginPage />, errorElement: <RouteError /> },
  {
    element: <RequireAuth />,
    errorElement: <RouteError />,
    children: [
      {
        element: <AppShell />,
        children: [
          // Run result pages are readable by both roles (admin read-only).
          ...MODULES.map((m) => ({ path: `/courses/:id/${MODULE_PATH[m]}/:runId`, element: page(RunPage, { module: m }) })),
          {
            element: <RequireRole role="faculty" />,
            children: [
              { path: '/courses', element: <CoursesPage /> },
              { path: '/dashboard', element: page(DashboardPage) },
              { path: '/courses/:id', element: page(CoursePage) },
              { path: '/courses/:id/exam-audit/compare', element: page(ComparePage) },
              ...MODULES.map((m) => ({ path: `/courses/:id/${MODULE_PATH[m]}/new`, element: page(NewRunPage, { module: m }) })),
            ],
          },
          {
            element: <RequireRole role="admin" />,
            children: [
              { path: '/admin', element: page(AdminUsersPage) },
              { path: '/admin/runs', element: page(AdminRunsPage) },
              { path: '/admin/usage', element: page(AdminUsagePage) },
              { path: '/admin/seed', element: page(AdminSeedPage) },
              { path: '/admin/department', element: page(AdminDepartmentPage) },
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
