'use client';

import React, { useState } from 'react';
import { useBlueprintStore } from '@/store/use-blueprint-store';
import { cn } from '@/lib/utils';
import { 
  Dna, 
  Menu, 
  Plus, 
  Activity, 
  LayoutTemplate, 
  ScrollText, 
  ChevronLeft, 
  ChevronRight,
  GitBranch,
  Network,
  TrendingUp,
  LineChart,
  Award,
  Sparkles
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { StageName } from '@/types/blueprint';
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
    activeStage, 
    sidebarOpen, 
    toggleSidebar, 
    setActiveStage,
    createNewProject,
    setActiveProject
  } = useBlueprintStore();

  const activeProject = projects.find(p => p.id === activeProjectId);

  const stages: { name: StageName; label: string; icon: React.ComponentType<any> }[] = [
    { name: 'dna-analyzer', label: '1. DNA Analyzer', icon: Dna },
    { name: 'feature-extractor', label: '2. Feature Extractor', icon: GitBranch },
    { name: 'roadmap', label: '3. Roadmap Generator', icon: LineChart },
    { name: 'team-structure', label: '4. Team Structure', icon: Network },
    { name: 'swot', label: '5. SWOT Analysis', icon: TrendingUp },
    { name: 'cost-estimator', label: '6. Cost Estimator', icon: Award },
    { name: 'final-blueprint', label: '7. Final Blueprint', icon: ScrollText },
  ];

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
        "h-full flex flex-col bg-card/68 backdrop-blur-md border-r border-border transition-all duration-300 shadow-lvl-3 z-30",
        sidebarOpen ? "w-[260px]" : "w-[68px]"
      )}
    >
      {/* Header Log Area */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-border">
        {sidebarOpen && (
          <span className="font-sans font-semibold text-sm tracking-tight text-primary flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-accent-blue animate-pulse" />
            Evolution Engine
          </span>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="h-8 w-8 hover:bg-black/5"
        >
          {sidebarOpen ? <ChevronLeft className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </Button>
      </div>

      {/* New Project CTA */}
      <div className="p-3">
        <Button
          onClick={handleNewProject}
          variant="outline"
          className={cn(
            "w-full flex items-center justify-center gap-2 rounded-md transition-all duration-200 border-border/80 shadow-lvl-1",
            sidebarOpen ? "px-4" : "p-2"
          )}
        >
          <Plus className="h-4 w-4 text-accent-blue" />
          {sidebarOpen && <span className="text-xs font-medium">New Startup</span>}
        </Button>
      </div>

      {/* Nav Stages */}
      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        {activeProject && (
          <div className="py-2">
            {sidebarOpen && (
              <span className="text-[10px] font-semibold tracking-wider text-muted-foreground uppercase px-3 block mb-2">
                Active Blueprint
              </span>
            )}
            {stages.map((stage, idx) => {
              const Icon = stage.icon;
              const isActive = activeStage === stage.name;
              
              // Dependency checking: check if all preceding stages are completed
              let isLocked = false;
              if (idx > 0) {
                const precedingStages = stages.slice(0, idx);
                const hasUncompletedPredecessor = precedingStages.some((s) => {
                  if (s.name === 'dna-analyzer') return !activeProject.dna;
                  if (s.name === 'feature-extractor') return !activeProject.features;
                  if (s.name === 'roadmap') return !activeProject.roadmap;
                  if (s.name === 'team-structure') return !activeProject.team;
                  if (s.name === 'swot') return !activeProject.swot;
                  if (s.name === 'cost-estimator') return !activeProject.cost;
                  return false;
                });
                isLocked = hasUncompletedPredecessor;
              }

              // Also lock when project is generating to prevent tab switches
              const isGenerating = activeProject.status === 'generating';
              const isDisabled = isLocked || isGenerating;

              return (
                <button
                  key={stage.name}
                  disabled={isDisabled}
                  onClick={() => setActiveStage(stage.name)}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2 rounded-md text-left transition-all duration-150 text-sm",
                    isActive 
                      ? "bg-accent-foreground/10 text-accent-blue font-medium" 
                      : isDisabled
                        ? "opacity-50 cursor-not-allowed text-muted-foreground/60"
                        : "text-muted-foreground hover:bg-black/5"
                  )}
                >
                  <Icon className={cn("h-4 w-4 shrink-0", isActive ? "text-accent-blue" : "text-muted-foreground")} />
                  {sidebarOpen && (
                    <span className="truncate flex-1 flex justify-between items-center">
                      <span>{stage.label}</span>
                      {isLocked && <span className="text-xs text-muted-foreground/50 ml-1">🔒</span>}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Projects Index */}
        <div className="pt-4 border-t border-border/50">
          {sidebarOpen && (
            <span className="text-[10px] font-semibold tracking-wider text-muted-foreground uppercase px-3 block mb-2">
              Recent Projects
            </span>
          )}
          <div className="space-y-0.5">
            {projects.map((proj) => (
              <button
                key={proj.id}
                onClick={() => setActiveProject(proj.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded-md text-left transition-all duration-150 text-xs",
                  activeProjectId === proj.id 
                    ? "bg-black/5 text-primary font-medium" 
                    : "text-muted-foreground hover:bg-black/5"
                )}
              >
                <Activity className="h-4 w-4 shrink-0" />
                {sidebarOpen && <span className="truncate flex-1">{proj.name}</span>}
              </button>
            ))}
            {projects.length === 0 && sidebarOpen && (
              <span className="text-xs text-muted-foreground/60 italic px-3 block">
                No active projects.
              </span>
            )}
          </div>
        </div>
      </div>
      {/* New Startup Dialog */}
      <Dialog open={newProjectOpen} onOpenChange={setNewProjectOpen}>
        <DialogContent className="sm:max-w-[420px] bg-card/95 backdrop-blur-md border border-border shadow-lvl-3 rounded-xl p-0 overflow-hidden">
          <form onSubmit={handleCreateProject}>
            <DialogHeader className="p-6 pb-2">
              <DialogTitle className="text-base font-bold tracking-tight text-primary flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-accent-blue" />
                <span>Initialize Startup Concept</span>
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Set up a new venture workspace. The engine will compile your strategic blueprints step-by-step.
              </DialogDescription>
            </DialogHeader>

            <div className="px-6 py-2 space-y-4">
              <div className="space-y-1">
                <label className="text-[10px] font-semibold text-muted-foreground uppercase">Startup Name</label>
                <Input
                  required
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="e.g. Solarify Maintenance"
                  className="h-9 text-xs"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-semibold text-muted-foreground uppercase">Core Vision / Concept</label>
                <Textarea
                  required
                  value={projectPrompt}
                  onChange={(e) => setProjectPrompt(e.target.value)}
                  placeholder="Describe your startup concept, target audience, pricing model, and competitive edge..."
                  className="text-xs min-h-[90px]"
                />
              </div>
            </div>

            <DialogFooter className="mt-6 border-t border-border/40 p-4 bg-muted/40 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setNewProjectOpen(false)}
                className="text-xs h-8 px-4 border-border"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isCreating || !projectName.trim() || !projectPrompt.trim()}
                className="text-xs h-8 px-4"
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
