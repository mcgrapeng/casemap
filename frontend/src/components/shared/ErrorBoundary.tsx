import * as React from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface State {
  error: Error | null;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // ponytail: console.error is fine for v1; central reporting when needed.
    console.error('ErrorBoundary caught:', error, info);
  }

  reset = () => this.setState({ hasError: false, error: null });

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return <ErrorFallback error={this.state.error} onReset={this.reset} />;
    }
    return this.props.children;
  }
}

export function ErrorFallback({ error, onReset }: { error: State['error']; onReset?: () => void }) {
  return (
    <div
      role="alert"
      className="flex min-h-[200px] flex-col items-center justify-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center"
    >
      <AlertTriangle className="h-8 w-8 text-destructive" aria-hidden="true" />
      <h2 className="text-lg font-semibold">Something went wrong</h2>
      <p className="max-w-md text-sm text-muted-foreground">
        {error?.message ?? 'An unexpected error occurred.'}
      </p>
      {onReset && (
        <Button variant="outline" onClick={onReset}>
          Try again
        </Button>
      )}
    </div>
  );
}
