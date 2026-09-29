import { cn } from '@/lib/utils';
import { LucideIcon, FileText, FolderOpen, AlertCircle, Inbox } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  variant?: 'default' | 'error' | 'search';
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  variant = 'default',
  className,
}: EmptyStateProps) {
  const defaultIcons = {
    default: Inbox,
    error: AlertCircle,
    search: FileText,
  };

  const IconComponent = Icon || defaultIcons[variant];

  return (
    <div className={cn(
      'flex flex-col items-center justify-center py-12 px-4 text-center',
      className
    )}>
      <div className={cn(
        'flex items-center justify-center w-16 h-16 rounded-2xl mb-4',
        variant === 'error' ? 'bg-red-50 dark:bg-red-900/20' : 'bg-muted'
      )}>
        <IconComponent className={cn(
          'w-8 h-8',
          variant === 'error' ? 'text-red-500' : 'text-muted-foreground'
        )} />
      </div>
      <h3 className="text-sm font-semibold text-foreground mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-muted-foreground max-w-sm mb-4">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="btn-primary"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

// Specialized empty states
export function EmptyProjectState({ onCreate }: { onCreate: () => void }) {
  return (
    <EmptyState
      icon={FolderOpen}
      title="No projects yet"
      description="Create your first startup project to begin building your AI-powered blueprint."
      action={{
        label: 'Create Project',
        onClick: onCreate,
      }}
    />
  );
}

export function EmptySearchState({ query }: { query: string }) {
  return (
    <EmptyState
      variant="search"
      title="No results found"
      description={`No results for "${query}". Try adjusting your search terms.`}
    />
  );
}

export function ErrorState({ 
  message, 
  onRetry 
}: { 
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <EmptyState
      variant="error"
      title="Something went wrong"
      description={message || "An unexpected error occurred. Please try again."}
      action={onRetry ? {
        label: 'Try Again',
        onClick: onRetry,
      } : undefined}
    />
  );
}
