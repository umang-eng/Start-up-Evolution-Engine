'use client';

import React, { useState } from 'react';
import { useBlueprintStore } from '@/store/use-blueprint-store';
import { cn } from '@/lib/utils';
import { 
  TrendingUp, 
  TrendingDown, 
  Users, 
  DollarSign, 
  Target, 
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  Sparkles,
  BarChart3,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge, StatusBadge, MetricBadge } from '@/components/ui/badge';
import { ProgressRing, ProgressBar } from '@/components/ui/progress';
import { EmptyProjectState } from '@/components/ui/empty-state';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { StartupProject } from '@/types/blueprint';
import { usePipelineStore } from '@/store/use-pipeline-store';

const PROJECT_STAGES = [
  { key: 'dna', stage: 'dna', label: 'DNA' },
  { key: 'features', stage: 'features', label: 'Features' },
  { key: 'roadmap', stage: 'roadmap', label: 'Roadmap' },
  { key: 'team', stage: 'team', label: 'Team' },
  { key: 'swot', stage: 'swot', label: 'SWOT' },
  { key: 'cost', stage: 'cost', label: 'Costs' },
  { key: 'legalCompliance', stage: 'legal_compliance', label: 'Legal' },
  { key: 'competitiveMoat', stage: 'competitive_moat', label: 'Moat' },
  { key: 'stressTest', stage: 'stress_test', label: 'Stress Test' },
  { key: 'financialIntelligence', stage: 'financial_intelligence', label: 'Financials' },
  { key: 'investmentCommittee', stage: 'investment_committee', label: 'Investment' },
  { key: 'productExecution', stage: 'product_execution', label: 'Execution' },
  { key: 'globalExpansion', stage: 'global_expansion', label: 'Expansion' },
  { key: 'blueprintCompiled', stage: 'blueprint', label: 'Blueprint' },
] as const satisfies ReadonlyArray<{ key: keyof StartupProject; stage: string; label: string }>;

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  description?: string;
}

function StatCard({ title, value, change, icon, trend, description }: StatCardProps) {
  return (
    <Card className="relative overflow-hidden">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-semibold text-foreground">{value}</p>
            {change !== undefined && (
              <div className="flex items-center gap-1">
                {trend === 'up' ? (
                  <TrendingUp className="h-3 w-3 text-emerald-500" />
                ) : trend === 'down' ? (
                  <TrendingDown className="h-3 w-3 text-red-500" />
                ) : null}
                <span className={cn(
                  'text-xs font-medium',
                  trend === 'up' && 'text-emerald-500',
                  trend === 'down' && 'text-red-500',
                  trend === 'neutral' && 'text-muted-foreground',
                )}>
                  {change > 0 ? '+' : ''}{change}%
                </span>
              </div>
            )}
          </div>
          <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
            {icon}
          </div>
        </div>
        {description && (
          <p className="text-xs text-muted-foreground mt-3">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}

interface ProjectCardProps {
  project: StartupProject;
  onClick: () => void;
}

function ProjectCard({ project, onClick }: ProjectCardProps) {
  const pipeline = usePipelineStore((state) => state.activePipelines[project.id]);
  const storedCompletedStageKeys = PROJECT_STAGES
    .filter(({ key }) => Boolean(project[key]))
    .map(({ key }) => key);
  const liveCompletedStageNames = new Set(
    Object.values(pipeline?.stages ?? {})
      .filter((stage) => stage.status === 'completed' || stage.status === 'cached')
      .map((stage) => stage.stage),
  );
  const completedStageKeys = PROJECT_STAGES
    .filter(({ key, stage }) => storedCompletedStageKeys.includes(key) || liveCompletedStageNames.has(stage))
    .map(({ key }) => key);
  const completedStages = completedStageKeys.length;
  const currentStage = PROJECT_STAGES.find(({ stage }) => stage === pipeline?.currentStage);
  const currentStageIsComplete = currentStage && completedStageKeys.includes(currentStage.key);
  const inProgressFraction = pipeline?.status === 'running' && currentStage && !currentStageIsComplete
    ? 0.5
    : 0;
  const progress = ((completedStages + inProgressFraction) / PROJECT_STAGES.length) * 100;
  const isComplete = completedStageKeys.length === PROJECT_STAGES.length;
  const badgeStatus = project.status === 'generating'
    ? 'running'
    : project.status === 'error'
      ? 'failed'
      : isComplete
        ? 'completed'
        : 'active';

  return (
    <Card 
      className="cursor-pointer hover:shadow-md transition-all duration-200 hover:border-primary/20"
      onClick={onClick}
    >
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="text-sm font-bold text-primary">
                {project.name.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h3 className="font-semibold text-foreground">{project.name}</h3>
              <p className="text-xs text-muted-foreground line-clamp-1">
                {project.dna?.valueProposition || project.ideaPrompt || 'No description'}
              </p>
            </div>
          </div>
          <ProgressRing value={progress} size={48} strokeWidth={3} />
        </div>
        
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-medium">
              {completedStages}/{PROJECT_STAGES.length} stages
              {pipeline?.status === 'running' && currentStage && (
                <span className="ml-1 text-xs text-primary">
                  · Generating {currentStage.label}
                </span>
              )}
            </span>
          </div>
          <ProgressBar value={progress} size="sm" />
          
          <div className="flex flex-wrap gap-1.5 pt-2">
            {PROJECT_STAGES.map(({ key, label }) => (
              completedStageKeys.includes(key) && (
                <Badge key={key} variant="success" size="sm">{label}</Badge>
              )
            ))}
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
          <StatusBadge status={badgeStatus} />
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </div>
      </CardContent>
    </Card>
  );
}

interface CreateProjectDialogProps {
  open: boolean;
  projectName: string;
  startupPrompt: string;
  creating: boolean;
  error: string | null;
  onOpenChange: (open: boolean) => void;
  onProjectNameChange: (value: string) => void;
  onPromptChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
}

function CreateProjectDialog({
  open,
  projectName,
  startupPrompt,
  creating,
  error,
  onOpenChange,
  onProjectNameChange,
  onPromptChange,
  onSubmit,
}: CreateProjectDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Describe your startup</DialogTitle>
          <DialogDescription>
            Enter the idea, problem, audience, or product concept you want the AI pipeline to analyze.
            Nothing will be generated until you submit this prompt.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="project-name" className="text-sm font-medium">Project name <span className="text-muted-foreground">(optional)</span></label>
            <Input
              id="project-name"
              value={projectName}
              onChange={(event) => onProjectNameChange(event.target.value)}
              placeholder="Name your venture"
              maxLength={255}
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="startup-prompt" className="text-sm font-medium">Startup prompt</label>
            <Textarea
              id="startup-prompt"
              value={startupPrompt}
              onChange={(event) => onPromptChange(event.target.value)}
              placeholder="Describe the startup idea you want to turn into a complete blueprint..."
              minLength={10}
              maxLength={1000}
              rows={6}
              required
              autoFocus
            />
            <p className="text-xs text-muted-foreground">{startupPrompt.length}/1000 characters</p>
          </div>
          {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={creating || startupPrompt.trim().length < 10}>
              {creating ? 'Creating...' : 'Create project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function ExecutiveDashboard() {
  const { projects, setActiveProject, createNewProject } = useBlueprintStore();
  const [createOpen, setCreateOpen] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [startupPrompt, setStartupPrompt] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const openCreateDialog = () => {
    setProjectName('');
    setStartupPrompt('');
    setCreateError(null);
    setCreateOpen(true);
  };

  const createFromPrompt = async (event: React.FormEvent) => {
    event.preventDefault();
    const prompt = startupPrompt.trim();
    if (!prompt) {
      setCreateError('Enter a startup idea or product concept before creating the project.');
      return;
    }

    const derivedName = projectName.trim() || prompt.split(/\s+/).slice(0, 6).join(' ');
    setCreating(true);
    setCreateError(null);
    try {
      await createNewProject(derivedName.length >= 3 ? derivedName : `${derivedName} Project`, prompt);
      setCreateOpen(false);
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : 'Unable to create the project.');
    } finally {
      setCreating(false);
    }
  };

  const totalProjects = projects.length;
  const completedProjects = projects.filter((project) =>
    PROJECT_STAGES.every(({ key }) => Boolean(project[key]))
  ).length;
  const activeProjects = totalProjects - completedProjects;

  // Calculate total features across all projects
  const totalFeatures = projects.reduce((acc, p) => 
    acc + (p.features?.features?.length || 0), 0
  );

  // Calculate total costs across all projects
  const totalCosts = projects.reduce((acc, p) => 
    acc + (p.cost?.year1Cost || 0), 0
  );

  if (totalProjects === 0) {
    return (
      <>
        <div className="flex-1 flex items-center justify-center p-8">
          <EmptyProjectState onCreate={openCreateDialog} />
        </div>
        <CreateProjectDialog
          open={createOpen}
          projectName={projectName}
          startupPrompt={startupPrompt}
          creating={creating}
          error={createError}
          onOpenChange={setCreateOpen}
          onProjectNameChange={setProjectName}
          onPromptChange={setStartupPrompt}
          onSubmit={createFromPrompt}
        />
      </>
    );
  }

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-7xl mx-auto p-6 space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Overview of your startup portfolio
            </p>
          </div>
          <button
            onClick={openCreateDialog}
            className="btn-primary gap-2"
          >
            <Sparkles className="h-4 w-4" />
            New Startup
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Projects"
            value={totalProjects}
            icon={<Target className="h-5 w-5" />}
            description="Active startup ventures"
          />
          <StatCard
            title="In Progress"
            value={activeProjects}
            icon={<Clock className="h-5 w-5" />}
            description="Currently being developed"
          />
          <StatCard
            title="Completed"
            value={completedProjects}
            icon={<CheckCircle2 className="h-5 w-5" />}
            description="Fully analyzed"
          />
          <StatCard
            title="Total Features"
            value={totalFeatures}
            icon={<Zap className="h-5 w-5" />}
            description="Across all projects"
          />
        </div>

        {/* Projects Grid */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-foreground">Your Projects</h2>
            <span className="text-sm text-muted-foreground">{totalProjects} total</span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onClick={() => setActiveProject(project.id)}
              />
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button 
                onClick={() => {
                  // Find first project with features to show analytics
                  const projectWithFeatures = projects.find(p => p.features || p.dna);
                  if (projectWithFeatures) {
                    setActiveProject(projectWithFeatures.id);
                  }
                }}
                className="flex items-center gap-3 p-4 rounded-xl border border-border hover:bg-muted transition-colors text-left cursor-pointer"
              >
                <div className="h-10 w-10 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                  <BarChart3 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <span className="text-sm font-medium text-foreground block">View Analytics</span>
                  <span className="text-xs text-muted-foreground">Portfolio insights</span>
                </div>
              </button>
              <button 
                onClick={() => {
                  // Find first project with team structure
                  const projectWithTeam = projects.find(p => p.team);
                  if (projectWithTeam) {
                    setActiveProject(projectWithTeam.id);
                  }
                }}
                className="flex items-center gap-3 p-4 rounded-xl border border-border hover:bg-muted transition-colors text-left cursor-pointer"
              >
                <div className="h-10 w-10 rounded-xl bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
                  <Users className="h-5 w-5 text-violet-600 dark:text-violet-400" />
                </div>
                <div>
                  <span className="text-sm font-medium text-foreground block">Team Review</span>
                  <span className="text-xs text-muted-foreground">Organization planning</span>
                </div>
              </button>
              <button 
                onClick={() => {
                  // Find first project with cost data
                  const projectWithCosts = projects.find(p => p.cost);
                  if (projectWithCosts) {
                    setActiveProject(projectWithCosts.id);
                  }
                }}
                className="flex items-center gap-3 p-4 rounded-xl border border-border hover:bg-muted transition-colors text-left cursor-pointer"
              >
                <div className="h-10 w-10 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                  <DollarSign className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <span className="text-sm font-medium text-foreground block">Financial Overview</span>
                  <span className="text-xs text-muted-foreground">Cost analysis</span>
                </div>
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
      <CreateProjectDialog
        open={createOpen}
        projectName={projectName}
        startupPrompt={startupPrompt}
        creating={creating}
        error={createError}
        onOpenChange={setCreateOpen}
        onProjectNameChange={setProjectName}
        onPromptChange={setStartupPrompt}
        onSubmit={createFromPrompt}
      />
    </div>
  );
}
