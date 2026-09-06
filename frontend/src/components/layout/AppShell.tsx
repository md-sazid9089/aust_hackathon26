import { NavLink, Outlet, useLocation, useParams } from 'react-router-dom';
import { BookOpen, ClipboardCheck, GitCompare, LayoutDashboard, LogOut, Moon, Scale, Shield, Sun, Target, Users, Activity, Building2, RotateCcw, BarChart3 } from 'lucide-react';
import { useAuth } from '@/auth/AuthProvider';
import { useTheme } from '@/hooks/useTheme';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/primitives';
import { AssistantWidget } from '@/components/assistant/AssistantWidget';
import { cn } from '@/lib/format';

const linkCls = ({ isActive }: { isActive: boolean }) =>
  cn(
    'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-fast cursor-pointer [&_svg]:size-[18px] [&_svg]:shrink-0',
    isActive ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground',
  );

function CourseNav({ courseId }: { courseId: string }) {
  const base = `/courses/${courseId}`;
  return (
    <div className="mt-6">
      <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">This course</p>
      <nav aria-label="Course modules" className="flex flex-col gap-0.5">
        <NavLink to={base} end className={linkCls}>
          <BookOpen aria-hidden /> Overview
        </NavLink>
        <NavLink to={`${base}/exam-audit/new`} className={linkCls}>
          <ClipboardCheck aria-hidden /> Exam audit
        </NavLink>
        <NavLink to={`${base}/attainment/new`} className={linkCls}>
          <Target aria-hidden /> Attainment
        </NavLink>
        <NavLink to={`${base}/syllabus-check/new`} className={linkCls}>
          <GitCompare aria-hidden /> Syllabus check
        </NavLink>
        <NavLink to={`${base}/calibration/new`} className={linkCls}>
          <Scale aria-hidden /> Calibration
        </NavLink>
      </nav>
    </div>
  );
}

export function AppShell() {
  const { profile, signOut } = useAuth();
  const { theme, toggle } = useTheme();
  const { id: courseId } = useParams();
  const loc = useLocation();
  const isAdmin = profile?.role === 'admin';
  const inCourse = courseId && loc.pathname.startsWith('/courses/');

  return (
    <div className="flex min-h-dvh bg-background text-foreground">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <aside className="hidden w-64 shrink-0 flex-col border-r bg-card md:flex" aria-label="Primary">
        <div className="flex h-16 items-center gap-2 border-b px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <ClipboardCheck className="h-4 w-4" aria-hidden />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-semibold">Faculty Copilot</p>
            <p className="text-xs text-muted-foreground">AUST · CSE</p>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          <nav aria-label="Main" className="flex flex-col gap-0.5">
            {!isAdmin && (
              <>
                <NavLink to="/courses" end className={linkCls}>
                  <BookOpen aria-hidden /> My courses
                </NavLink>
                <NavLink to="/dashboard" className={linkCls}>
                  <LayoutDashboard aria-hidden /> Dashboard
                </NavLink>
              </>
            )}
            {isAdmin && (
              <>
                <NavLink to="/admin" end className={linkCls}>
                  <Users aria-hidden /> Users
                </NavLink>
                <NavLink to="/admin/runs" className={linkCls}>
                  <Activity aria-hidden /> Runs
                </NavLink>
                <NavLink to="/admin/usage" className={linkCls}>
                  <BarChart3 aria-hidden /> Usage
                </NavLink>
                <NavLink to="/admin/department" className={linkCls}>
                  <Building2 aria-hidden /> Department
                </NavLink>
                <NavLink to="/admin/seed" className={linkCls}>
                  <RotateCcw aria-hidden /> Demo data
                </NavLink>
              </>
            )}
          </nav>
          {inCourse && !isAdmin && <CourseNav courseId={courseId} />}
        </div>
        <div className="border-t p-3">
          <div className="flex items-center gap-3 px-2 py-1">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold">{(profile?.full_name ?? profile?.email ?? '?').slice(0, 1).toUpperCase()}</div>
            <div className="min-w-0 flex-1 leading-tight">
              <p className="truncate text-sm font-medium">{profile?.full_name}</p>
              <p className="truncate text-xs text-muted-foreground">{profile?.email}</p>
            </div>
            {isAdmin && (
              <Badge variant="secondary">
                <Shield className="h-3 w-3" aria-hidden /> Admin
              </Badge>
            )}
          </div>
          <div className="mt-2 flex items-center gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon-sm" onClick={toggle} aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
                  {theme === 'dark' ? <Sun aria-hidden /> : <Moon aria-hidden />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{theme === 'dark' ? 'Light theme' : 'Dark theme'}</TooltipContent>
            </Tooltip>
            <Button variant="ghost" size="sm" className="ml-auto" onClick={() => void signOut()}>
              <LogOut aria-hidden /> Sign out
            </Button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-3 border-b bg-card px-4 md:hidden">
          <ClipboardCheck className="h-5 w-5 text-primary" aria-hidden />
          <p className="text-sm font-semibold">Faculty Copilot</p>
          <div className="ml-auto flex items-center gap-1">
            <Button variant="ghost" size="icon-sm" onClick={toggle} aria-label="Toggle theme">
              {theme === 'dark' ? <Sun aria-hidden /> : <Moon aria-hidden />}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => void signOut()}>
              <LogOut aria-hidden />
              <span className="sr-only">Sign out</span>
            </Button>
          </div>
        </header>
        <nav aria-label="Main (mobile)" className="flex gap-1 overflow-x-auto border-b bg-card px-2 py-1 md:hidden">
          {isAdmin ? (
            <>
              <NavLink to="/admin" end className={linkCls}>Users</NavLink>
              <NavLink to="/admin/runs" className={linkCls}>Runs</NavLink>
              <NavLink to="/admin/usage" className={linkCls}>Usage</NavLink>
              <NavLink to="/admin/department" className={linkCls}>Dept</NavLink>
              <NavLink to="/admin/seed" className={linkCls}>Demo</NavLink>
            </>
          ) : (
            <>
              <NavLink to="/courses" end className={linkCls}>Courses</NavLink>
              <NavLink to="/dashboard" className={linkCls}>Dashboard</NavLink>
              {inCourse && (
                <>
                  <NavLink to={`/courses/${courseId}`} end className={linkCls}>Overview</NavLink>
                  <NavLink to={`/courses/${courseId}/exam-audit/new`} className={linkCls}>Audit</NavLink>
                  <NavLink to={`/courses/${courseId}/attainment/new`} className={linkCls}>Attainment</NavLink>
                  <NavLink to={`/courses/${courseId}/syllabus-check/new`} className={linkCls}>Syllabus</NavLink>
                  <NavLink to={`/courses/${courseId}/calibration/new`} className={linkCls}>Calibration</NavLink>
                </>
              )}
            </>
          )}
        </nav>
        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 md:px-8 md:py-8 focus:outline-none">
          <Outlet />
        </main>
      </div>
      <AssistantWidget />
    </div>
  );
}
