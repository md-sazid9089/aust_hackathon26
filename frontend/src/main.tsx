import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import '@fontsource/atkinson-hyperlegible/400.css';
import '@fontsource/atkinson-hyperlegible/700.css';
import '@fontsource-variable/crimson-pro/index.css';
import '@fontsource-variable/noto-sans-bengali/index.css';
import './index.css';
import { queryClient } from '@/lib/query-client';
import { AuthProvider } from '@/auth/AuthProvider';
import { TooltipProvider } from '@/components/ui/primitives';
import { AppRouter } from './router';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider delayDuration={200}>
          <AppRouter />
        </TooltipProvider>
      </AuthProvider>
      <Toaster richColors position="bottom-right" closeButton toastOptions={{ duration: 5000 }} />
    </QueryClientProvider>
  </React.StrictMode>,
);
