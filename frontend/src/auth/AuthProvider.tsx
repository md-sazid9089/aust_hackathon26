import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { Session } from '@supabase/supabase-js';
import { ApiContext, ApiError, type Api } from '@/lib/api';
import { HttpApi } from '@/lib/api/http';
import { getSupabase } from '@/lib/supabase';
import type { Profile } from '@/lib/types/api';

const LOCAL_TOKEN_KEY = 'fc-local-token';
const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api/v1';
/** Pairs with backend `AUTH_MODE`: `dev` = no token, fixed faculty user (never in prod); `local` = email+password → HS256 JWT from `/auth/login`; `supabase` = Supabase Auth session. */
export type AuthMode = 'dev' | 'local' | 'supabase';
const rawAuthMode = import.meta.env.VITE_AUTH_MODE as string | undefined;
export const AUTH_MODE: AuthMode = rawAuthMode === 'dev' || rawAuthMode === 'local' ? rawAuthMode : 'supabase';

interface AuthState {
  status: 'loading' | 'anonymous' | 'authenticated';
  profile: Profile | null;
  authMode: AuthMode;
  lastError: string | null;
  signInDev: () => Promise<void>;
  signInWithPassword: (email: string, password: string) => Promise<string | null>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<Profile | null>;
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
  const [lastError, setLastError] = useState<string | null>(null);

  const clear = useCallback(() => {
    sessionStorage.removeItem(LOCAL_TOKEN_KEY);
    setApi(null);
    setProfile(null);
    setStatus('anonymous');
  }, []);

  /* ---- local mode (backend AUTH_MODE=local, HS256 JWT from /auth/login) ---- */
  const bootLocal = useCallback(
    async (token: string, attempt = 0) => {
      sessionStorage.setItem(LOCAL_TOKEN_KEY, token);
      const http = new HttpApi(BASE_URL, async () => sessionStorage.getItem(LOCAL_TOKEN_KEY), clear);
      try {
        const p = await http.me();
        setApi(http);
        setProfile(p);
        setStatus('authenticated');
      } catch (e) {
        // A rejected token is final; a backend hiccup (restart, 5xx, network) is not — retry briefly, then keep the token.
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) return clear();
        if (attempt < 2) {
          await new Promise((r) => setTimeout(r, 1500 * (attempt + 1)));
          return bootLocal(token, attempt + 1);
        }
        setLastError(e instanceof Error ? e.message : 'Backend unreachable');
        setApi(null);
        setProfile(null);
        setStatus('anonymous');
      }
    },
    [clear],
  );

  const signInLocal = useCallback(
    async (email: string, password: string): Promise<string | null> => {
      setLastError(null);
      let res: Response;
      try {
        res = await fetch(`${BASE_URL}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
      } catch {
        return 'Backend unreachable';
      }
      if (!res.ok) {
        try {
          const body = (await res.json()) as { error?: { message?: string } };
          return body.error?.message ?? res.statusText;
        } catch {
          return res.statusText || 'Sign-in failed';
        }
      }
      const { access_token } = (await res.json()) as { access_token: string };
      await bootLocal(access_token);
      return null;
    },
    [bootLocal],
  );

  /* ---- dev mode (backend AUTH_MODE=dev, no token) ---- */
  const signInDev = useCallback(async () => {
    setStatus('loading');
    setLastError(null);
    const http = new HttpApi(BASE_URL, async () => null, clear);
    try {
      const p = await http.me();
      setApi(http);
      setProfile(p);
      setStatus('authenticated');
    } catch (e) {
      setLastError(e instanceof Error ? e.message : 'Backend unreachable');
      setApi(null);
      setProfile(null);
      setStatus('anonymous');
    }
  }, [clear]);

  /* ---- supabase mode ---- */
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
      } catch (e) {
        setLastError(e instanceof Error ? e.message : 'Backend unreachable');
        // Keep the Supabase session unless the backend actually rejected it.
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) return void sb.auth.signOut().then(clear);
        setApi(null);
        setProfile(null);
        setStatus('anonymous');
      }
    },
    [clear],
  );

  useEffect(() => {
    if (AUTH_MODE === 'dev') {
      void signInDev();
      return;
    }
    if (AUTH_MODE === 'local') {
      const saved = sessionStorage.getItem(LOCAL_TOKEN_KEY);
      if (saved) void bootLocal(saved);
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
  }, [bootLive, bootLocal, clear, signInDev]);

  const signInWithPassword = useCallback(
    async (email: string, password: string) => {
      if (AUTH_MODE === 'local') return signInLocal(email, password);
      const sb = getSupabase();
      if (!sb) return 'Supabase is not configured (VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY).';
      const { error } = await sb.auth.signInWithPassword({ email, password });
      return error ? error.message : null;
    },
    [signInLocal],
  );

  const signOut = useCallback(async () => {
    const sb = AUTH_MODE === 'supabase' ? getSupabase() : null;
    if (sb) await sb.auth.signOut();
    clear();
  }, [clear]);

  const refreshProfile = useCallback(async () => {
    if (!api) return null;
    try {
      const p = await api.me();
      setProfile(p);
      return p;
    } catch {
      return null;
    }
  }, [api]);

  const value = useMemo<AuthState>(
    () => ({ status, profile, authMode: AUTH_MODE, lastError, signInDev, signInWithPassword, signOut, refreshProfile }),
    [status, profile, lastError, signInDev, signInWithPassword, signOut, refreshProfile],
  );

  return (
    <AuthCtx.Provider value={value}>
      <ApiContext.Provider value={api}>{children}</ApiContext.Provider>
    </AuthCtx.Provider>
  );
}
