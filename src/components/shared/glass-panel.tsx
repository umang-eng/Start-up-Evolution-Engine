import React from 'react';
import { cn } from '@/lib/utils';

interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  opacity?: number;
  blur?: string;
  shadow?: 'lvl-1' | 'lvl-2' | 'lvl-3' | 'lvl-4';
}

export function GlassPanel({
  children,
  className,
  shadow = 'lvl-1',
  ...props
}: GlassPanelProps) {
  return (
    <div
      className={cn(
        'liquid-glass rounded-lg transition-all duration-200',
        {
          'shadow-lvl-1': shadow === 'lvl-1',
          'shadow-lvl-2': shadow === 'lvl-2',
          'shadow-lvl-3': shadow === 'lvl-3',
          'shadow-lvl-4': shadow === 'lvl-4',
        },
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
