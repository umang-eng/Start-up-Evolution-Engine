import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-secondary text-secondary-foreground',
        secondary: 'bg-secondary text-secondary-foreground',
        primary: 'bg-primary text-primary-foreground',
        success: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
        warning: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
        destructive: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
        info: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400',
        outline: 'border border-border text-foreground',
        ghost: 'text-muted-foreground',
      },
      size: {
        sm: 'px-2 py-0.5 text-[10px]',
        md: 'px-2.5 py-0.5 text-xs',
        lg: 'px-3 py-1 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

export function Badge({
  className,
  variant,
  size,
  dot,
  children,
  ...props
}: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props}>
      {dot && (
        <span className={cn(
          'mr-1.5 h-1.5 w-1.5 rounded-full',
          variant === 'success' && 'bg-emerald-500',
          variant === 'warning' && 'bg-amber-500',
          variant === 'destructive' && 'bg-red-500',
          variant === 'info' && 'bg-sky-500',
          variant === 'primary' && 'bg-primary-foreground/50',
          variant === 'default' && 'bg-foreground/50',
          variant === 'outline' && 'bg-foreground/50',
          variant === 'ghost' && 'bg-foreground/50',
        )} />
      )}
      {children}
    </div>
  );
}

// Specific badge components for common use cases
export function StatusBadge({ 
  status, 
  label 
}: { 
  status: 'active' | 'completed' | 'pending' | 'failed' | 'running';
  label?: string;
}) {
  const variants = {
    active: 'info',
    completed: 'success',
    pending: 'warning',
    failed: 'destructive',
    running: 'primary',
  } as const;

  const labels = {
    active: 'Active',
    completed: 'Completed',
    pending: 'Pending',
    failed: 'Failed',
    running: 'Running',
  };

  return (
    <Badge variant={variants[status]} dot>
      {label || labels[status]}
    </Badge>
  );
}

export function MetricBadge({ 
  value, 
  trend,
  label 
}: { 
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  label?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-semibold text-foreground">{value}</span>
      {trend && (
        <span className={cn(
          'text-xs font-medium',
          trend === 'up' && 'text-emerald-600',
          trend === 'down' && 'text-red-600',
          trend === 'neutral' && 'text-muted-foreground',
        )}>
          {trend === 'up' && '↑'}
          {trend === 'down' && '↓'}
          {trend === 'neutral' && '→'}
        </span>
      )}
      {label && (
        <span className="text-xs text-muted-foreground">{label}</span>
      )}
    </div>
  );
}
