import type { ReactNode } from 'react';
import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react';

type AlertVariant = 'info' | 'success' | 'warning' | 'error';

interface AlertBoxProps {
  variant?: AlertVariant;
  title?: string;
  children?: ReactNode;
  items?: string[];
  className?: string;
}

const config: Record<AlertVariant, { classes: string; Icon: typeof Info }> = {
  info: { classes: 'bg-blue-50 border-blue-200 text-blue-800', Icon: Info },
  success: { classes: 'bg-green-50 border-green-200 text-green-800', Icon: CheckCircle },
  warning: { classes: 'bg-amber-50 border-amber-200 text-amber-800', Icon: AlertTriangle },
  error: { classes: 'bg-red-50 border-red-200 text-red-800', Icon: XCircle },
};

export function AlertBox({ variant = 'info', title, children, items, className = '' }: AlertBoxProps) {
  const { classes, Icon } = config[variant];
  return (
    <div className={`rounded-lg border p-4 ${classes} ${className}`}>
      <div className="flex gap-3">
        <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          {title && <p className="font-semibold mb-1">{title}</p>}
          {children && <div className="text-sm">{children}</div>}
          {items && items.length > 0 && (
            <ul className="text-sm mt-1 space-y-1 list-disc list-inside">
              {items.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
