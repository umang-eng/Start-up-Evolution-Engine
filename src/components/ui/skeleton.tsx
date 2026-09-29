import { cn } from '@/lib/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  lines?: number;
}

export function Skeleton({
  className,
  variant = 'rectangular',
  width,
  height,
  lines = 1,
  ...props
}: SkeletonProps) {
  if (variant === 'text' && lines > 1) {
    return (
      <div className={cn('space-y-2', className)} {...props}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="skeleton h-4"
            style={{
              width: i === lines - 1 ? '70%' : '100%',
            }}
          />
        ))}
      </div>
    );
  }

  const baseClasses = cn(
    'skeleton',
    {
      'rounded-full': variant === 'circular',
      'rounded-lg': variant === 'rounded',
      'rounded': variant === 'rectangular' || variant === 'text',
    },
    className
  );

  return (
    <div
      className={baseClasses}
      style={{
        width: width || (variant === 'circular' ? 40 : '100%'),
        height: height || (variant === 'circular' ? 40 : variant === 'text' ? 16 : 200),
      }}
      {...props}
    />
  );
}

// Composite Skeleton Components
export function CardSkeleton() {
  return (
    <div className="card-premium p-6 space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton variant="text" width={120} height={20} />
        <Skeleton variant="circular" width={32} height={32} />
      </div>
      <Skeleton variant="text" lines={3} />
      <div className="flex gap-2">
        <Skeleton variant="rounded" width={80} height={28} />
        <Skeleton variant="rounded" width={80} height={28} />
      </div>
    </div>
  );
}

export function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="space-y-3">
      <div className="flex gap-4 pb-3 border-b border-border">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} variant="text" height={16} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          {Array.from({ length: columns }).map((_, j) => (
            <Skeleton key={j} variant="text" height={16} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function StatSkeleton() {
  return (
    <div className="card-premium p-6">
      <div className="flex items-center justify-between mb-4">
        <Skeleton variant="text" width={100} height={14} />
        <Skeleton variant="circular" width={40} height={40} />
      </div>
      <Skeleton variant="text" width={60} height={32} />
      <Skeleton variant="text" width={80} height={12} className="mt-2" />
    </div>
  );
}

export function ListSkeleton({ items = 4 }: { items?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton variant="circular" width={36} height={36} />
          <div className="flex-1 space-y-2">
            <Skeleton variant="text" height={14} />
            <Skeleton variant="text" height={12} width="60%" />
          </div>
        </div>
      ))}
    </div>
  );
}
