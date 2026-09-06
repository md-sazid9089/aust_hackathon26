import { QueryClient } from '@tanstack/react-query';
import { ApiError } from '@/lib/api';

export const queryClient = new QueryClient({
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
