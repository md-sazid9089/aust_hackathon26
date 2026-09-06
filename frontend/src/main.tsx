import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
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
