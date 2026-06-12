'use client';

import React from 'react';
import { useBlueprintStore } from '@/store/use-blueprint-store';
import { cn } from '@/lib/utils';
import { 
  Search, 
  Bell, 
  Share2, 
  Download, 
  Sparkles,
  ChevronDown
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export function Navbar() {
  const { projects, activeProjectId, sidebarOpen } = useBlueprintStore();
  const activeProject = projects.find(p => p.id === activeProjectId);

  return (
    <header className="h-14 w-full flex items-center justify-between px-6 bg-card/75 backdrop-blur-md border-b border-border shadow-lvl-1 z-20">
      {/* Left Workspace Switcher */}
      <div className="flex items-center gap-3">
        <div className="h-7 w-7 rounded-md bg-accent-blue flex items-center justify-center text-white text-[11px] font-bold shadow-lvl-1">
          SE
        </div>
        <div className="flex items-center gap-1.5 cursor-pointer hover:bg-black/5 px-2 py-1 rounded-md transition-all">
          <span className="text-xs font-semibold text-primary">
            {activeProject ? activeProject.name : 'Personal Workspace'}
          </span>
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        </div>
      </div>

      {/* Center Action Pipeline Search */}
      <div className="flex-1 max-w-md mx-6 hidden md:block">
        <div className="relative flex items-center w-full h-8 px-3 rounded-md border border-border/80 bg-surface-secondary text-muted-foreground hover:border-standard cursor-pointer transition-all">
          <Search className="h-3.5 w-3.5 mr-2" />
          <span className="text-xs flex-1">Search blueprint features, costs...</span>
          <kbd className="h-5 px-1.5 rounded bg-black/5 border border-border text-[9px] font-sans flex items-center">
            ⌘K
          </kbd>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2">
        {activeProject && (
          <>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs gap-1.5 hover:bg-black/5 text-muted-foreground"
            >
              <Share2 className="h-3.5 w-3.5 text-accent-blue" />
              <span className="hidden sm:inline">Share</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs gap-1.5 hover:bg-black/5 text-muted-foreground"
            >
              <Download className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Export</span>
            </Button>
          </>
        )}

        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 hover:bg-black/5 text-muted-foreground"
        >
          <Bell className="h-4 w-4" />
        </Button>

        {/* User Profile Avatar */}
        <div className="h-8 w-8 rounded-full border border-border overflow-hidden cursor-pointer hover:border-standard transition-all">
          <img
            src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&q=80"
            alt="User avatar"
            className="h-full w-full object-cover"
          />
        </div>
      </div>
    </header>
  );
}
