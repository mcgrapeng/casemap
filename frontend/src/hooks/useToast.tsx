// Lightweight toast hook built on Radix Toast primitives.
import * as React from 'react';
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
  type ToastProps,
} from '@/components/ui/toast';

interface ToastItem {
  id: string;
  title?: string;
  description?: string;
  variant?: ToastProps['variant'];
  duration?: number;
}

type ToastAction =
  | { type: 'add'; toast: ToastItem }
  | { type: 'remove'; id: string }
  | { type: 'clear' };

interface ToastContextValue {
  toast: (t: Omit<ToastItem, 'id'>) => void;
  dismiss: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function ToastRoot({ children }: { children: React.ReactNode }) {
  const [items, dispatch] = React.useReducer(
    (state: ToastItem[], action: ToastAction): ToastItem[] => {
      switch (action.type) {
        case 'add':
          return [...state, action.toast];
        case 'remove':
          return state.filter((t) => t.id !== action.id);
        case 'clear':
          return [];
      }
    },
    [],
  );

  const value = React.useMemo<ToastContextValue>(
    () => ({
      toast: (t) =>
        dispatch({
          type: 'add',
          toast: { ...t, id: Math.random().toString(36).slice(2, 9) },
        }),
      dismiss: (id) => dispatch({ type: 'remove', id }),
    }),
    [],
  );

  return (
    <ToastContext.Provider value={value}>
      <ToastProvider>
        {children}
        {items.map((t) => (
          <Toast
            key={t.id}
            variant={t.variant}
            duration={t.duration ?? 4000}
            onOpenChange={(open) => {
              if (!open) value.dismiss(t.id);
            }}
          >
            <div className="grid gap-1">
              {t.title && <ToastTitle>{t.title}</ToastTitle>}
              {t.description && <ToastDescription>{t.description}</ToastDescription>}
            </div>
            <ToastClose />
          </Toast>
        ))}
        <ToastViewport />
      </ToastProvider>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastRoot');
  return ctx;
}
