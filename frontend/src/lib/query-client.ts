import { MutationCache, QueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ApiError } from '@/lib/api';

/** Human-readable message for a failed request; 422s surface the first field problem instead of the generic envelope text. */
export function describeError(err: unknown): string {
  if (!(err instanceof ApiError)) return err instanceof Error ? err.message : 'Something went wrong';
  const errors = (err.details as { errors?: { loc?: (string | number)[]; msg?: string }[] } | undefined)?.errors;
  if (err.status === 422 && errors?.length) {
    const e = errors[0];
    const field = (e.loc ?? []).filter((p) => p !== 'body').map((p) => (typeof p === 'number' ? `row ${p + 1}` : p)).join(' › ');
    const msg = (e.msg ?? '').replace(/^Value error, /, '');
    return field ? `${field}: ${msg}` : msg || err.message;
  }
  return `${err.message}${err.requestId ? ` (request ${err.requestId.slice(0, 8)})` : ''}`;
}

export const queryClient = new QueryClient({
  // Safety net: a failed mutation must never be silent. Call-sites that pass their own onError opt out.
  mutationCache: new MutationCache({
    onError: (err, _vars, _ctx, mutation) => {
      if (mutation.options.onError) return;
      toast.error(describeError(err));
    },
  }),
  defaultOptions: {
    queries: {
      // Navigating back to a page within a minute renders instantly from cache; mutations invalidate explicitly.
      staleTime: 60_000,
      gcTime: 10 * 60_000,
      retry: (count, err) => {
        if (err instanceof ApiError && err.status < 500) return false;
        return count < 1;
      },
      retryDelay: 500,
      refetchOnWindowFocus: false,
      refetchOnReconnect: 'always',
    },
    mutations: { retry: 0 },
  },
});
