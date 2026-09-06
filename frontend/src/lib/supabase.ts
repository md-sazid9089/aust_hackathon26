import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseKey =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ||
  '';

if (!supabaseUrl || !supabaseKey) {
  // Gracefully inform during development or test execution without crashing module evaluation
  console.warn(
    '[Supabase] Warning: VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY is missing. ' +
      'Check frontend/.env.local or frontend/.env.',
  );
}

/**
 * Dedicated Supabase client for Authentication and session management.
 * In Faculty Assessment Copilot, Supabase JS is used strictly for Auth.
 * Business queries and mutations flow through the FastAPI backend at /api/v1.
 */
// createClient throws on empty args; placeholders keep the SPA rendering when env is unset (mock mode, misconfigured deploy)
export const supabase = createClient(
  supabaseUrl || 'https://placeholder.supabase.co',
  supabaseKey || 'placeholder-anon-key',
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  },
);
