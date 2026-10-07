import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
import { AuthProvider } from '@/components/providers/ApiProvider';
import { ThemeProvider } from '@/hooks/useTheme';
import { ToastRoot } from '@/hooks/useToast';
import HomePage from '@/pages/HomePage';
import NewProjectPage from '@/pages/NewProjectPage';
import ProjectPage from '@/pages/ProjectPage';
import CasesPage from '@/pages/CasesPage';
import ProgressPage from '@/pages/ProgressPage';
import ReportPage from '@/pages/ReportPage';

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ToastRoot>
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/projects/new" element={<NewProjectPage />} />
                <Route path="/projects/:id" element={<ProjectPage />} />
                <Route path="/projects/:id/cases" element={<CasesPage />} />
                <Route path="/projects/:id/progress" element={<ProgressPage />} />
                <Route path="/projects/:id/report" element={<ReportPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </BrowserRouter>
          </ToastRoot>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
