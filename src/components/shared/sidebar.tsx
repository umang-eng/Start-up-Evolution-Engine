'use client';

import React, { useState } from 'react';
import { useBlueprintStore } from '@/store/use-blueprint-store';
import { cn } from '@/lib/utils';
import { 
  Dna, 
  Menu, 
  Plus, 
  Activity, 
  ChevronLeft, 
  ChevronRight,
  GitBranch,
  Network,
  TrendingUp,
  LineChart,
  Award,
  Sparkles,
  Mic,
  LayoutDashboard,
  Settings,
  HelpCircle,
  Search
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SettingsDialog } from './settings-dialog';
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
import { Badge } from '@/components/ui/badge';

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

  const stages: { name: StageName; label: string; icon: React.ComponentType<any>; shortLabel: string }[] = [
    { name: 'dna-analyzer', label: 'DNA Analyzer', icon: Dna, shortLabel: 'DNA' },
    { name: 'feature-extractor', label: 'Feature Extractor', icon: GitBranch, shortLabel: 'Features' },
    { name: 'roadmap', label: 'Roadmap', icon: LineChart, shortLabel: 'Roadmap' },
    { name: 'team-structure', label: 'Team Structure', icon: Network, shortLabel: 'Team' },
    { name: 'swot', label: 'SWOT Analysis', icon: TrendingUp, shortLabel: 'SWOT' },
    { name: 'cost-estimator', label: 'Cost Estimator', icon: Award, shortLabel: 'Costs' },
    { name: 'final-blueprint', label: 'Final Blueprint', icon: Sparkles, shortLabel: 'Blueprint' },
  ];

  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [projectPrompt, setProjectPrompt] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

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

  // Count completed stages
  const completedStages = activeProject ? stages.filter(s => {
    if (s.name === 'dna-analyzer') return !!activeProject.dna;
    if (s.name === 'feature-extractor') return !!activeProject.features;
    if (s.name === 'roadmap') return !!activeProject.roadmap;
    if (s.name === 'team-structure') return !!activeProject.team;
    if (s.name === 'swot') return !!activeProject.swot;
    if (s.name === 'cost-estimator') return !!activeProject.cost;
    return false;
  }).length : 0;

  return (
    <aside
      className={cn(
        "h-full flex flex-col bg-card border-r border-border transition-all duration-300 z-30",
        sidebarOpen ? "w-[260px]" : "w-[68px]"
      )}
    >
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-border">
        {sidebarOpen ? (
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-primary flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-semibold text-sm text-foreground">
              Evolution Engine
            </span>
          </div>
        ) : (
          <div className="h-7 w-7 rounded-lg bg-primary flex items-center justify-center mx-auto">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </div>
        )}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={toggleSidebar}
          className={cn(!sidebarOpen && "mx-auto")}
        >
          {sidebarOpen ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </Button>
      </div>

      {/* New Project CTA */}
      <div className="p-3">
        <Button
          onClick={handleNewProject}
          variant="default"
          className={cn(
            "w-full gap-2",
            !sidebarOpen && "px-0 justify-center"
          )}
        >
          <Plus className="h-4 w-4" />
          {sidebarOpen && <span>New Startup</span>}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 space-y-1">
        {/* Dashboard Link */}
        <a
          href="/"
          className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
            "text-muted-foreground hover:text-foreground hover:bg-muted",
          )}
        >
          <LayoutDashboard className="h-4 w-4 shrink-0" />
          {sidebarOpen && <span>Dashboard</span>}
        </a>

        {/* Stages */}
        {activeProject && (
          <div className="pt-4">
            {sidebarOpen && (
              <div className="flex items-center justify-between px-3 mb-2">
                <span className="text-overline">Active Blueprint</span>
                <Badge variant="secondary" size="sm">
                  {completedStages}/{stages.length}
                </Badge>
              </div>
            )}
            <div className="space-y-0.5">
              {stages.map((stage, idx) => {
                const Icon = stage.icon;
                const isActive = activeStage === stage.name;
                
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

                const isCompleted = (() => {
                  if (stage.name === 'dna-analyzer') return !!activeProject.dna;
                  if (stage.name === 'feature-extractor') return !!activeProject.features;
                  if (stage.name === 'roadmap') return !!activeProject.roadmap;
                  if (stage.name === 'team-structure') return !!activeProject.team;
                  if (stage.name === 'swot') return !!activeProject.swot;
                  if (stage.name === 'cost-estimator') return !!activeProject.cost;
                  return false;
                })();

                return (
                  <button
                    key={stage.name}
                    disabled={isLocked}
                    onClick={() => setActiveStage(stage.name)}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-all text-sm",
                      isActive 
                        ? "bg-primary/10 text-primary font-medium" 
                        : isLocked
                          ? "opacity-40 cursor-not-allowed text-muted-foreground"
                          : "text-muted-foreground hover:text-foreground hover:bg-muted"
                    )}
                  >
                    <div className={cn(
                      "h-6 w-6 rounded-md flex items-center justify-center shrink-0",
                      isActive ? "bg-primary/20" : "bg-muted",
                      isCompleted && !isActive && "bg-emerald-100 dark:bg-emerald-900/30"
                    )}>
                      {isCompleted && !isActive ? (
                        <svg className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <Icon className={cn("h-3.5 w-3.5", isActive ? "text-primary" : "text-muted-foreground")} />
                      )}
                    </div>
                    {sidebarOpen && (
                      <span className="truncate flex-1">{stage.label}</span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Conversation Intelligence */}
        {sidebarOpen && (
          <div className="pt-4">
            <span className="text-overline px-3 block mb-2">Intelligence</span>
            <a
              href="/meetings"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <div className="h-6 w-6 rounded-md bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
                <Mic className="h-3.5 w-3.5 text-violet-600 dark:text-violet-400" />
              </div>
              <span>Meetings</span>
            </a>
          </div>
        )}

        {/* Projects List */}
        {sidebarOpen && projects.length > 0 && (
          <div className="pt-4">
            <span className="text-overline px-3 block mb-2">Recent Projects</span>
            <div className="space-y-0.5">
              {projects.slice(0, 5).map((proj) => (
                <button
                  key={proj.id}
                  onClick={() => setActiveProject(proj.id)}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors text-sm",
                    activeProjectId === proj.id 
                      ? "bg-muted text-foreground font-medium" 
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  <div className="h-6 w-6 rounded-md bg-muted flex items-center justify-center shrink-0">
                    <Activity className="h-3.5 w-3.5" />
                  </div>
                  <span className="truncate">{proj.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* Bottom Actions */}
      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon-sm" className="flex-1" onClick={() => setSettingsOpen(true)}>
            <Settings className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon-sm" className="flex-1" onClick={() => setHelpOpen(true)}>
            <HelpCircle className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* New Startup Dialog */}
      <Dialog open={newProjectOpen} onOpenChange={setNewProjectOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <form onSubmit={handleCreateProject}>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                Create New Startup
              </DialogTitle>
              <DialogDescription>
                Set up a new venture workspace. The engine will compile your strategic blueprints step-by-step.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">Startup Name</label>
                <Input
                  required
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="e.g. Solarify Maintenance"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">Core Vision</label>
                <Textarea
                  required
                  value={projectPrompt}
                  onChange={(e) => setProjectPrompt(e.target.value)}
                  placeholder="Describe your startup concept, target audience, pricing model, and competitive edge..."
                  className="min-h-[100px]"
                />
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setNewProjectOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isCreating || !projectName.trim() || !projectPrompt.trim()}
              >
                {isCreating ? 'Creating...' : 'Create Workspace'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />

      <Dialog open={helpOpen} onOpenChange={setHelpOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <HelpCircle className="h-5 w-5 text-primary" />
              Help & Keyboard Shortcuts
            </DialogTitle>
            <DialogDescription>
              Quick reference for navigating the Evolution Engine.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4 text-sm">
            <div className="flex justify-between"><span className="text-muted-foreground">Create new project</span><kbd className="px-2 py-0.5 rounded bg-muted text-xs font-mono">Sidebar + button</kbd></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Navigate stages</span><kbd className="px-2 py-0.5 rounded bg-muted text-xs font-mono">Click stage in sidebar</kbd></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Collapse sidebar</span><kbd className="px-2 py-0.5 rounded bg-muted text-xs font-mono">Chevron icon</kbd></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Open settings</span><kbd className="px-2 py-0.5 rounded bg-muted text-xs font-mono">Gear icon (bottom)</kbd></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Record meeting</span><kbd className="px-2 py-0.5 rounded bg-muted text-xs font-mono">Mic icon in navbar</kbd></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setHelpOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  );
}
