import { lazy, Suspense, type ComponentType } from 'react';
import { createBrowserRouter, Link, Navigate, RouterProvider, useRouteError } from 'react-router-dom';
import { FileQuestion } from 'lucide-react';
import { RequireAuth, RequireRole } from '@/auth/guards';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState, ErrorState } from '@/components/feedback/states';
import { Button } from '@/components/ui/button';
import { LoginPage } from '@/features/auth/LoginPage';
import { MODULE_PATH } from '@/lib/format';
import type { RunModule } from '@/lib/types/api';

// Route-level code splitting: only login ships in the initial bundle.
const LandingPage = lazy(() => import('@/features/landing/LandingPage'));
const CoursesPage = lazy(() => import('@/features/courses/CoursesPage').then((m) => ({ default: m.CoursesPage })));
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

import { Skeleton } from '@/components/ui/table';

// Route preloaders for instant zero-latency navigation on hover/focus
export const preloadLanding = () => import('@/features/landing/LandingPage');
export const preloadCourses = () => import('@/features/courses/CoursesPage');
export const preloadCourse = () => import('@/features/courses/CoursePage');
export const preloadNewRun = () => import('@/features/runs/NewRunPage');
export const preloadRun = () => import('@/features/runs/RunPage');
export const preloadCompare = () => import('@/features/runs/ComparePage');
export const preloadDashboard = () => import('@/features/dashboard/DashboardPage');
export const preloadAdmin = () => import('@/features/admin/AdminPages');

export function PageFallback() {
  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8 animate-fade-in" role="status" aria-live="polite">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48 sm:w-64" />
          <Skeleton className="h-4 w-72 sm:w-96" />
        </div>
        <Skeleton className="h-10 w-28 rounded-lg" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="rounded-xl border bg-card/60 p-5 shadow-sm space-y-3">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-3 w-40" />
          </div>
        ))}
      </div>
      <div className="rounded-xl border bg-card/60 p-6 shadow-sm space-y-4">
        <Skeleton className="h-6 w-40" />
        <div className="space-y-3 pt-2">
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-12 w-full rounded-lg" />
        </div>
      </div>
      <span className="sr-only">Loading page...</span>
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
              { path: '/courses', element: page(CoursesPage) },
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
