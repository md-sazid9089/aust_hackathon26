import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';
import LandingPage from '@/features/landing/LandingPage';

const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { path: '*', element: <Navigate to="/" replace /> },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
