import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider';
import type { AppRole } from '@/lib/types/api';
import { LoadingState } from '@/components/feedback/states';

export function RequireAuth() {
  const { status } = useAuth();
  const loc = useLocation();
  if (status === 'loading')
    return (
      <div className="mx-auto max-w-3xl p-8">
        <LoadingState label="Signing in" />
      </div>
    );
  if (status === 'anonymous') return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return <Outlet />;
}

export function RequireRole({ role }: { role: AppRole }) {
  const { profile } = useAuth();
  if (!profile) return null;
  if (profile.role !== role) return <Navigate to={profile.role === 'admin' ? '/admin' : '/courses'} replace />;
  return <Outlet />;
}
