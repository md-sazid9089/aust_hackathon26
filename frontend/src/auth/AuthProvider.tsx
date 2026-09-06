import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { Session } from '@supabase/supabase-js';
import { API_MODE, ApiContext, type Api } from '@/lib/api';
import { HttpApi } from '@/lib/api/http';
import { MockApi } from '@/lib/api/mock/MockApi';
import { ids } from '@/lib/api/mock/fixtures';
import { getSupabase } from '@/lib/supabase';
import type { Profile } from '@/lib/types/api';

const MOCK_USER_KEY = 'fc-mock-user';
const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api/v1';

export const DEMO_USERS = [
  { id: ids.faculty, label: 'Faculty', hint: 'Dr. Farhana Rahman · owns CSE 2201 & CSE 2101' },
  { id: ids.admin, label: 'Admin', hint: 'Prof. Kamal Hossain · read-only department view' },
] as const;

interface AuthState {
  status: 'loading' | 'anonymous' | 'authenticated';
  profile: Profile | null;
  mode: 'mock' | 'live';
  signInMock: (userId: string) => void;
  signInWithPassword: (email: string, password: string) => Promise<string | null>;
  signOut: () => Promise<void>;
}

const AuthCtx = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const v = useContext(AuthCtx);
  if (!v) throw new Error('useAuth outside <AuthProvider>');
  return v;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthState['status']>('loading');
  const [profile, setProfile] = useState<Profile | null>(null);
  const [api, setApi] = useState<Api | null>(null);

  const clear = useCallback(() => {
    setApi(null);
    setProfile(null);
    setStatus('anonymous');
  }, []);

  /* ---- mock mode ---- */
  const signInMock = useCallback((userId: string) => {
    const mock = new MockApi(userId);
    sessionStorage.setItem(MOCK_USER_KEY, userId);
    setApi(mock);
    void mock.me().then((p) => {
      setProfile(p);
      setStatus('authenticated');
    });
  }, []);

  /* ---- live mode ---- */
  const bootLive = useCallback(
    async (session: Session | null) => {
      const sb = getSupabase();
      if (!sb || !session) return clear();
      const http = new HttpApi(
        BASE_URL,
        async () => (await sb.auth.getSession()).data.session?.access_token ?? null,
        () => void sb.auth.signOut().then(clear),
      );
      try {
        const p = await http.me();
        setApi(http);
        setProfile(p);
        setStatus('authenticated');
      } catch {
        clear();
      }
    },
    [clear],
  );

  useEffect(() => {
    if (API_MODE === 'mock') {
      const saved = sessionStorage.getItem(MOCK_USER_KEY);
      if (saved && (saved === ids.faculty || saved === ids.admin)) signInMock(saved);
      else setStatus('anonymous');
      return;
    }
    const sb = getSupabase();
    if (!sb) {
      setStatus('anonymous');
      return;
    }
    void sb.auth.getSession().then(({ data }) => bootLive(data.session));
    const { data: sub } = sb.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT') clear();
      if (event === 'SIGNED_IN') void bootLive(session);
    });
    return () => sub.subscription.unsubscribe();
  }, [bootLive, clear, signInMock]);

  const signInWithPassword = useCallback(async (email: string, password: string) => {
    const sb = getSupabase();
    if (!sb) return 'Supabase is not configured (VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY).';
    const { error } = await sb.auth.signInWithPassword({ email, password });
    return error ? error.message : null;
  }, []);

  const signOut = useCallback(async () => {
    sessionStorage.removeItem(MOCK_USER_KEY);
    const sb = API_MODE === 'live' ? getSupabase() : null;
    if (sb) await sb.auth.signOut();
    clear();
  }, [clear]);

  const value = useMemo<AuthState>(() => ({ status, profile, mode: API_MODE, signInMock, signInWithPassword, signOut }), [status, profile, signInMock, signInWithPassword, signOut]);

  return (
    <AuthCtx.Provider value={value}>
      <ApiContext.Provider value={api}>{children}</ApiContext.Provider>
    </AuthCtx.Provider>
  );
}
