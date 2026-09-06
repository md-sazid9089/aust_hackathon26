import { NavLink, Outlet, useLocation, useParams } from 'react-router-dom';
import { BookOpen, ClipboardCheck, GitCompare, LayoutDashboard, LogOut, Moon, Scale, Shield, Sun, Target, Users, Activity, Building2, RotateCcw, BarChart3 } from 'lucide-react';
import { useAuth } from '@/auth/AuthProvider';
import { useTheme } from '@/hooks/useTheme';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/primitives';
import { AssistantWidget } from '@/components/assistant/AssistantWidget';
import { cn } from '@/lib/format';
import { preloadAdmin, preloadCourse, preloadCourses, preloadDashboard, preloadNewRun } from '@/router';

const linkCls = ({ isActive }: { isActive: boolean }) =>
  cn(
    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-fast cursor-pointer active:scale-[0.98] [&_svg]:size-[18px] [&_svg]:shrink-0',
    isActive ? 'bg-primary/10 text-primary font-semibold shadow-xs' : 'text-muted-foreground hover:bg-muted/80 hover:text-foreground',
  );

function CourseNav({ courseId }: { courseId: string }) {
  const base = `/courses/${courseId}`;
  return (
    <div className="mt-6">
      <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">This course</p>
      <nav aria-label="Course modules" className="flex flex-col gap-0.5">
        <NavLink to={base} end className={linkCls} onMouseEnter={preloadCourse} onFocus={preloadCourse}>
          <BookOpen aria-hidden /> Overview
        </NavLink>
        <NavLink to={`${base}/exam-audit/new`} className={linkCls} onMouseEnter={preloadNewRun} onFocus={preloadNewRun}>
          <ClipboardCheck aria-hidden /> Exam audit
        </NavLink>
        <NavLink to={`${base}/attainment/new`} className={linkCls} onMouseEnter={preloadNewRun} onFocus={preloadNewRun}>
          <Target aria-hidden /> Attainment
        </NavLink>
        <NavLink to={`${base}/syllabus-check/new`} className={linkCls} onMouseEnter={preloadNewRun} onFocus={preloadNewRun}>
          <GitCompare aria-hidden /> Syllabus check
        </NavLink>
        <NavLink to={`${base}/calibration/new`} className={linkCls} onMouseEnter={preloadNewRun} onFocus={preloadNewRun}>
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
      <aside className="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col self-start border-r border-border/80 bg-card/95 backdrop-blur-md md:flex" aria-label="Primary">
        <div className="flex h-16 items-center gap-2 border-b px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground shadow-xs">
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
                <NavLink to="/courses" end className={linkCls} onMouseEnter={preloadCourses} onFocus={preloadCourses}>
                  <BookOpen aria-hidden /> My courses
                </NavLink>
                <NavLink to="/dashboard" className={linkCls} onMouseEnter={preloadDashboard} onFocus={preloadDashboard}>
                  <LayoutDashboard aria-hidden /> Dashboard
                </NavLink>
              </>
            )}
            {isAdmin && (
              <>
                <NavLink to="/admin" end className={linkCls} onMouseEnter={preloadAdmin} onFocus={preloadAdmin}>
                  <Users aria-hidden /> Users
                </NavLink>
                <NavLink to="/admin/runs" className={linkCls} onMouseEnter={preloadAdmin} onFocus={preloadAdmin}>
                  <Activity aria-hidden /> Runs
                </NavLink>
                <NavLink to="/admin/usage" className={linkCls} onMouseEnter={preloadAdmin} onFocus={preloadAdmin}>
                  <BarChart3 aria-hidden /> Usage
                </NavLink>
                <NavLink to="/admin/department" className={linkCls} onMouseEnter={preloadAdmin} onFocus={preloadAdmin}>
                  <Building2 aria-hidden /> Department
                </NavLink>
                <NavLink to="/admin/seed" className={linkCls} onMouseEnter={preloadAdmin} onFocus={preloadAdmin}>
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
        <header className="flex h-14 items-center gap-3 border-b border-border/80 bg-card/95 backdrop-blur-md px-4 md:hidden">
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
        <nav aria-label="Main (mobile)" className="no-scrollbar flex gap-1 overflow-x-auto border-b border-border/80 bg-card/95 backdrop-blur-md px-2 py-1 md:hidden">
          {isAdmin ? (
            <>
              <NavLink to="/admin" end className={linkCls} onMouseEnter={preloadAdmin} onFocus={preloadAdmin}>Users</NavLink>
              <NavLink to="/admin/runs" className={linkCls} onMouseEnter={preloadAdmin} onFocus={preloadAdmin}>Runs</NavLink>
              <NavLink to="/admin/usage" className={linkCls} onMouseEnter={preloadAdmin} onFocus={preloadAdmin}>Usage</NavLink>
              <NavLink to="/admin/department" className={linkCls} onMouseEnter={preloadAdmin} onFocus={preloadAdmin}>Dept</NavLink>
              <NavLink to="/admin/seed" className={linkCls} onMouseEnter={preloadAdmin} onFocus={preloadAdmin}>Demo</NavLink>
            </>
          ) : (
            <>
              <NavLink to="/courses" end className={linkCls} onMouseEnter={preloadCourses} onFocus={preloadCourses}>Courses</NavLink>
              <NavLink to="/dashboard" className={linkCls} onMouseEnter={preloadDashboard} onFocus={preloadDashboard}>Dashboard</NavLink>
              {inCourse && (
                <>
                  <NavLink to={`/courses/${courseId}`} end className={linkCls} onMouseEnter={preloadCourse} onFocus={preloadCourse}>Overview</NavLink>
                  <NavLink to={`/courses/${courseId}/exam-audit/new`} className={linkCls} onMouseEnter={preloadNewRun} onFocus={preloadNewRun}>Audit</NavLink>
                  <NavLink to={`/courses/${courseId}/attainment/new`} className={linkCls} onMouseEnter={preloadNewRun} onFocus={preloadNewRun}>Attainment</NavLink>
                  <NavLink to={`/courses/${courseId}/syllabus-check/new`} className={linkCls} onMouseEnter={preloadNewRun} onFocus={preloadNewRun}>Syllabus</NavLink>
                  <NavLink to={`/courses/${courseId}/calibration/new`} className={linkCls} onMouseEnter={preloadNewRun} onFocus={preloadNewRun}>Calibration</NavLink>
                </>
              )}
            </>
          )}
        </nav>
        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 md:px-8 md:py-8 focus:outline-none animate-fade-in">
          <Outlet />
        </main>
      </div>
      <AssistantWidget />
    </div>
  );
}
