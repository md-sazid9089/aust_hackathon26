import { supabase } from '@/lib/supabase';
import { HttpApi } from '@/lib/api/http';
import { MockApi } from '@/lib/api/mock/MockApi';
import { ApiError, type Api } from '@/lib/api/types';

const mode = import.meta.env.VITE_API_MODE;
const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/**
 * Global API client instance connecting frontend components to backend endpoints.
 * Automatically injects the active Supabase JWT Bearer token into outgoing requests.
 */
export const api: Api =
  mode === 'mock'
    ? new MockApi('prof.rahman')
    : new HttpApi(
        baseUrl,
        async () => {
          try {
            const { data } = await supabase.auth.getSession();
            return data.session?.access_token ?? null;
          } catch {
            return null;
          }
        },
        () => {
          // On 401 unauthorized, clear expired session
          supabase.auth.signOut().catch(() => {});
        },
      );

export { ApiError };
export type { Api };
