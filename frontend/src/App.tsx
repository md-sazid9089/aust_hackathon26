import { useState, useEffect } from 'react';
import type { Session } from '@supabase/supabase-js';
import { Link } from 'react-router-dom';
import { supabase } from './lib/supabase';
import { ShieldCheck, Database, Key, CheckCircle2, AlertCircle, LogIn, LogOut, Loader2, Sparkles, ArrowLeft } from 'lucide-react';

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    // 1. Check initial session
    async function initSession() {
      try {
        const { data, error } = await supabase.auth.getSession();
        if (error) {
          console.error('[Supabase Auth Error]', error);
          setAuthError(error.message);
        } else {
          setSession(data.session);
        }
      } catch (err: unknown) {
        setAuthError(err instanceof Error ? err.message : 'Failed to connect to Supabase Auth');
      } finally {
        setLoading(false);
      }
    }

    initSession();

    // 2. Subscribe to auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setAuthSuccess(null);
    setActionLoading(true);

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        setAuthError(error.message);
      } else if (data.user) {
        setAuthSuccess(`Welcome, ${data.user.email}!`);
      }
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : 'Sign in failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSignOut = async () => {
    setAuthError(null);
    setAuthSuccess(null);
    setActionLoading(true);
    try {
      await supabase.auth.signOut();
      setAuthSuccess('Signed out successfully.');
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : 'Sign out failed');
    } finally {
      setActionLoading(false);
    }
  };

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'Not configured';
  const hasKey = Boolean(
    import.meta.env.VITE_SUPABASE_ANON_KEY || import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
  );

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6 font-sans">
      <div className="w-full max-w-2xl mb-4">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 rounded-md text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="w-4 h-4" aria-hidden />
          Back to overview
        </Link>
      </div>
      <div className="w-full max-w-2xl bg-card border border-border rounded-xl shadow-lg overflow-hidden">
        {/* Header */}
        <div className="bg-[#1E3A5F] text-white px-8 py-6 flex items-center justify-between border-b border-slate-700">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="w-5 h-5 text-amber-400" />
              <span className="text-xs uppercase tracking-wider font-semibold text-amber-300">
                AUST Hackathon 2026
              </span>
            </div>
            <h1 className="text-2xl font-serif font-bold text-white tracking-tight">
              Faculty Assessment &amp; Curriculum Copilot
            </h1>
            <p className="text-sm text-slate-300 mt-1">
              Supabase Auth &amp; Project Connection Status
            </p>
          </div>
          <div className="h-12 w-12 rounded-lg bg-white/10 flex items-center justify-center border border-white/20">
            <ShieldCheck className="w-7 h-7 text-amber-300" />
          </div>
        </div>

        {/* Content */}
        <div className="p-8 space-y-6">
          {/* Connection Overview Card */}
          <div className="bg-slate-50 dark:bg-slate-800/60 rounded-lg p-5 border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-2">
                <Database className="w-4 h-4 text-[#1E3A5F] dark:text-sky-400" />
                Supabase Environment &amp; Auth Client
              </h2>
              {loading ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Connecting...
                </span>
              ) : hasKey ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Client Initialized
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Missing Keys
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="bg-white dark:bg-slate-900 p-3 rounded border border-slate-200 dark:border-slate-800">
                <div className="text-slate-500 dark:text-slate-400 font-medium">Supabase Project URL</div>
                <div className="font-mono text-slate-800 dark:text-slate-200 truncate mt-0.5" title={supabaseUrl}>
                  {supabaseUrl}
                </div>
              </div>
              <div className="bg-white dark:bg-slate-900 p-3 rounded border border-slate-200 dark:border-slate-800">
                <div className="text-slate-500 dark:text-slate-400 font-medium">Key Status</div>
                <div className="font-mono text-emerald-600 dark:text-emerald-400 flex items-center gap-1 mt-0.5">
                  <Key className="w-3.5 h-3.5" />
                  {hasKey ? 'Publishable / Anon Key Configured' : 'No Key Found'}
                </div>
              </div>
            </div>

            <div className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed bg-amber-50/70 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 rounded p-3">
              <span className="font-semibold text-amber-900 dark:text-amber-300">Architecture Notice (PROJECT_CONTEXT.md): </span>
              In this application, Supabase JS is dedicated to <strong>Authentication &amp; Session Management</strong>.
              All domain queries (courses, outcomes, question audits, attainment) route through the FastAPI backend at{' '}
              <code className="bg-white/60 dark:bg-slate-800 px-1 py-0.5 rounded font-mono">/api/v1</code> with RLS context.
            </div>
          </div>

          {/* Session / Auth Interaction Section */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-6 space-y-4">
            <h3 className="font-semibold text-base text-slate-800 dark:text-slate-200 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-[#1E3A5F] dark:text-sky-400" />
              Auth State &amp; Session Test
            </h3>

            {authError && (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs rounded-md flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            {authSuccess && (
              <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 text-emerald-700 dark:text-emerald-300 text-xs rounded-md flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{authSuccess}</span>
              </div>
            )}

            {session ? (
              <div className="space-y-4">
                <div className="p-4 bg-emerald-50/80 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900 rounded-lg">
                  <div className="text-xs font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
                    Active Faculty Session
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-200">
                    Logged in as: <span className="font-mono">{session.user.email}</span>
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-1 truncate">
                    User ID: {session.user.id}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleSignOut}
                  disabled={actionLoading}
                  className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-200 transition-colors disabled:opacity-50"
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <LogOut className="w-4 h-4" />}
                  Sign Out
                </button>
              </div>
            ) : (
              <form onSubmit={handleSignIn} className="space-y-4">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Enter your credentials to test live authentication with the connected Supabase instance:
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Faculty Email
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="faculty@aust.edu"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full text-sm px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#1E3A5F]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Password
                    </label>
                    <input
                      type="password"
                      required
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full text-sm px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#1E3A5F]"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <span className="text-xs text-slate-400 dark:text-slate-500">
                    Client: <code className="text-slate-600 dark:text-slate-400">@/lib/supabase</code>
                  </span>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="inline-flex items-center justify-center gap-2 px-5 py-2 text-sm font-medium rounded-md text-white bg-[#1E3A5F] hover:bg-[#162C46] dark:bg-sky-600 dark:hover:bg-sky-700 transition-colors shadow-sm disabled:opacity-50"
                  >
                    {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <LogIn className="w-4 h-4" />}
                    Sign In with Supabase
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
