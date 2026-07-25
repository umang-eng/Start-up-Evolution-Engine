'use client';

import React, { useState } from 'react';
import { useNotificationStore, type Notification } from '@/store/use-notification-store';
import { cn } from '@/lib/utils';
import { 
  Bell, 
  CheckCircle, 
  AlertTriangle, 
  Info, 
  X, 
  Check,
  Trash2 
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const ICON_MAP = {
  success: CheckCircle,
  error: AlertTriangle,
  warning: AlertTriangle,
  info: Info,
};

const COLOR_MAP = {
  success: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/20',
  error: 'text-red-500 bg-red-50 dark:bg-red-900/20',
  warning: 'text-amber-500 bg-amber-50 dark:bg-amber-900/20',
  info: 'text-sky-500 bg-sky-50 dark:bg-sky-900/20',
};

export function NotificationPanel() {
  const { 
    notifications, 
    unreadCount, 
    markAsRead, 
    markAllAsRead, 
    removeNotification,
    clearAll 
  } = useNotificationStore();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      {/* Trigger Button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setIsOpen(!isOpen)}
        className="relative"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-primary text-[10px] font-bold text-primary-foreground flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </Button>

      {/* Panel */}
      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)} 
          />
          <div className="absolute right-0 mt-2 w-[380px] bg-card border border-border rounded-xl shadow-xl z-50 animate-slide-down">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <span className="text-sm font-semibold text-foreground">Notifications</span>
              <div className="flex items-center gap-1">
                {unreadCount > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={markAllAsRead}
                    className="text-xs h-7"
                  >
                    <Check className="h-3 w-3 mr-1" />
                    Mark all read
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => setIsOpen(false)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Notifications List */}
            <div className="max-h-[400px] overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="py-12 text-center text-sm text-muted-foreground">
                  No notifications yet
                </div>
              ) : (
                notifications.map((notif) => (
                  <NotificationItem
                    key={notif.id}
                    notification={notif}
                    onRead={() => markAsRead(notif.id)}
                    onRemove={() => removeNotification(notif.id)}
                  />
                ))
              )}
            </div>

            {/* Footer */}
            {notifications.length > 0 && (
              <div className="px-4 py-2 border-t border-border">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearAll}
                  className="w-full text-xs text-muted-foreground"
                >
                  <Trash2 className="h-3 w-3 mr-1" />
                  Clear all
                </Button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function NotificationItem({ 
  notification, 
  onRead, 
  onRemove 
}: { 
  notification: Notification;
  onRead: () => void;
  onRemove: () => void;
}) {
  const Icon = ICON_MAP[notification.type];

  return (
    <div
      className={cn(
        'flex items-start gap-3 px-4 py-3 border-b border-border/50 hover:bg-muted/50 transition-colors cursor-pointer',
        !notification.read && 'bg-primary/5'
      )}
      onClick={onRead}
    >
      <div className={cn('h-8 w-8 rounded-lg flex items-center justify-center shrink-0', COLOR_MAP[notification.type])}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <span className="text-sm font-medium text-foreground block">{notification.title}</span>
          <button
            onClick={(e) => { e.stopPropagation(); onRemove(); }}
            className="text-muted-foreground hover:text-foreground shrink-0"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{notification.message}</p>
        <span className="text-[10px] text-muted-foreground/70 mt-1 block">
          {formatTimeAgo(notification.timestamp)}
        </span>
      </div>
      {!notification.read && (
        <div className="h-2 w-2 rounded-full bg-primary shrink-0 mt-2" />
      )}
    </div>
  );
}

function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (seconds < 60) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return date.toLocaleDateString();
}

// Browser notification permission request
export function requestNotificationPermission() {
  if ('Notification' in window && window.Notification.permission === 'default') {
    window.Notification.requestPermission();
  }
}
