import { createContext, useContext } from 'react';
import type { Api } from './types';

export type { Api, RunEventHandlers } from './types';
export { ApiError } from './types';

export const API_MODE: 'mock' | 'live' = (import.meta.env.VITE_API_MODE as string) === 'live' ? 'live' : 'mock';

export const ApiContext = createContext<Api | null>(null);

export function useApi(): Api {
  const api = useContext(ApiContext);
  if (!api) throw new Error('useApi must be used inside <AuthProvider>');
  return api;
}
