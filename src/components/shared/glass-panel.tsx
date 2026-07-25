import React from 'react';
import { cn } from '@/lib/utils';

interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  shadow?: 'sm' | 'md' | 'lg' | 'xl';
}

export function GlassPanel({
  children,
  className,
  shadow = 'sm',
  ...props
}: GlassPanelProps) {
  return (
    <div
      className={cn(
        'rounded-xl bg-card border border-border transition-all duration-200',
        {
          'shadow-sm': shadow === 'sm',
          'shadow-md': shadow === 'md',
          'shadow-lg': shadow === 'lg',
          'shadow-xl': shadow === 'xl',
        },
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
