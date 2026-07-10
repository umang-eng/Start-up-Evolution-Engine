'use client';

import React, { useState } from 'react';
import { useBlueprintStore } from '@/store/use-blueprint-store';
import { cn } from '@/lib/utils';
import { 
  Menu, 
  Plus, 
  Activity, 
  ChevronLeft, 
  Sparkles,
  Trash2,
  Circle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

export function Sidebar() {
  const { 
    projects, 
    activeProjectId, 
    sidebarOpen, 
    toggleSidebar, 
    createNewProject,
    setActiveProject,
    deleteProject
  } = useBlueprintStore();

  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [projectPrompt, setProjectPrompt] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const handleNewProject = () => {
    setProjectName('');
    setProjectPrompt('');
    setNewProjectOpen(true);
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim() || !projectPrompt.trim()) return;
    setIsCreating(true);
    try {
      await createNewProject(projectName.trim(), projectPrompt.trim());
      setNewProjectOpen(false);
    } catch (err) {
      console.error(err);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <aside
      className={cn(
        "h-full flex flex-col bg-card/60 backdrop-blur-xl border-r border-white/[0.04] transition-all duration-300 z-30",
        sidebarOpen ? "w-[220px]" : "w-[56px]"
      )}
    >
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-3 border-b border-white/[0.04]">
        {sidebarOpen && (
          <span className="font-sans font-semibold text-sm tracking-tight text-foreground flex items-center gap-2.5">
            <img src="/logo.png" alt="Evolution Engine Logo" className="h-5 w-5 object-contain rounded-md" />
            <span className="gradient-text font-bold">Evolution</span>
          </span>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="h-8 w-8 text-muted-foreground hover:text-foreground"
        >
          {sidebarOpen ? <ChevronLeft className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      </div>

      {/* New Project CTA */}
      <div className="p-3">
        <Button
          onClick={handleNewProject}
          variant="outline"
          className={cn(
            "w-full flex items-center justify-center gap-2 rounded-lg transition-all duration-200 border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05] hover:border-cyan-500/20",
            sidebarOpen ? "px-4 h-9" : "p-2 h-9 w-9"
          )}
        >
          <Plus className="h-5 w-5 text-cyan-400" />
          {sidebarOpen && <span className="text-sm font-medium text-foreground">New Startup</span>}
        </Button>
      </div>

      {/* Projects List */}
      <div className="flex-1 overflow-y-auto px-2 scrollbar-thin">
        <div className="py-2">
          {sidebarOpen && (
            <span className="text-sm font-semibold tracking-widest text-muted-foreground/90 uppercase px-2 block mb-2">
              Recent Projects
            </span>
          )}
          <div className="space-y-0.5">
            {projects.map((proj) => {
              const isActive = activeProjectId === proj.id;
              return (
                <div key={proj.id} className="relative group w-full">
                  <button
                    onClick={() => setActiveProject(proj.id)}
                    className={cn(
                      "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition-all duration-200 text-sm group-hover:pr-8 cursor-pointer border border-transparent",
                      isActive
                        ? "bg-white/[0.06] border-cyan-500/15 text-foreground font-medium pr-8"
                        : "text-muted-foreground hover:bg-white/[0.04] hover:text-foreground"
                    )}
                  >
                    <div className={cn(
                      "h-5 w-5 rounded-md flex items-center justify-center shrink-0",
                      isActive ? "bg-cyan-500/15" : "bg-white/[0.04]"
                    )}>
                      <Activity className={cn("h-5 w-5", isActive ? "text-cyan-400" : "text-muted-foreground/90")} />
                    </div>
                    {sidebarOpen && <span className="truncate flex-1">{proj.name}</span>}
                  </button>
                  {sidebarOpen && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm('Are you sure you want to delete this startup idea?')) {
                          deleteProject(proj.id);
                        }
                      }}
                      className={cn(
                        "absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors",
                        isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                      )}
                      title="Delete project"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              );
            })}
            {projects.length === 0 && sidebarOpen && (
              <span className="text-sm text-muted-foreground/80 italic px-2.5 block py-4 text-center">
                No active projects.
              </span>
            )}
          </div>
        </div>
      </div>

      {/* New Startup Dialog */}
      <Dialog open={newProjectOpen} onOpenChange={setNewProjectOpen}>
        <DialogContent className="sm:max-w-[420px] bg-card/95 backdrop-blur-xl border border-white/[0.08] shadow-lvl-3 rounded-xl p-0 overflow-hidden">
          <form onSubmit={handleCreateProject}>
            <DialogHeader className="p-6 pb-2">
              <DialogTitle className="text-sm font-bold tracking-tight text-foreground flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-cyan-400" />
                <span>Initialize Startup Concept</span>
              </DialogTitle>
              <DialogDescription className="text-sm text-muted-foreground">
                Set up a new venture workspace. The engine will compile strategic blueprints step-by-step.
              </DialogDescription>
            </DialogHeader>

            <div className="px-6 py-3 space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Startup Name</label>
                <Input
                  required
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="e.g. Solarify Maintenance"
                  className="h-9 text-sm bg-white/[0.03] border-white/[0.06]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Core Vision / Concept</label>
                <Textarea
                  required
                  value={projectPrompt}
                  onChange={(e) => setProjectPrompt(e.target.value)}
                  placeholder="Describe your startup concept, target audience, pricing model, and competitive edge..."
                  className="text-sm min-h-[90px] bg-white/[0.03] border-white/[0.06]"
                />
              </div>
            </div>

            <DialogFooter className="mt-4 border-t border-white/[0.04] p-4 bg-white/[0.02] flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setNewProjectOpen(false)}
                className="text-sm h-8 px-4 border-white/[0.06]"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isCreating || !projectName.trim() || !projectPrompt.trim()}
                className="text-sm h-8 px-4"
              >
                {isCreating ? 'Creating Workspace...' : 'Launch Workspace'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </aside>
  );
}
