'use client';

import React from 'react';
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
  project: {
    id: string;
    name: string;
    status?: string;
    dna?: any;
    features?: any;
    roadmap?: any;
    team?: any;
    swot?: any;
    cost?: any;
  };
  onClick: () => void;
}

function ProjectCard({ project, onClick }: ProjectCardProps) {
  const completedStages = [
    project.dna,
    project.features,
    project.roadmap,
    project.team,
    project.swot,
    project.cost,
  ].filter(Boolean).length;

  const progress = (completedStages / 6) * 100;

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
                {project.dna?.valueProposition || 'No description'}
              </p>
            </div>
          </div>
          <ProgressRing value={progress} size={48} strokeWidth={3} />
        </div>
        
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-medium">{completedStages}/6 stages</span>
          </div>
          <ProgressBar value={progress} size="sm" />
          
          <div className="flex flex-wrap gap-1.5 pt-2">
            {project.dna && <Badge variant="success" size="sm">DNA</Badge>}
            {project.features && <Badge variant="success" size="sm">Features</Badge>}
            {project.roadmap && <Badge variant="success" size="sm">Roadmap</Badge>}
            {project.team && <Badge variant="success" size="sm">Team</Badge>}
            {project.swot && <Badge variant="success" size="sm">SWOT</Badge>}
            {project.cost && <Badge variant="success" size="sm">Costs</Badge>}
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
          <StatusBadge status={completedStages === 6 ? 'completed' : 'active'} />
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </div>
      </CardContent>
    </Card>
  );
}

export function ExecutiveDashboard() {
  const { projects, setActiveProject, createNewProject } = useBlueprintStore();

  const totalProjects = projects.length;
  const completedProjects = projects.filter(p => 
    p.dna && p.features && p.roadmap && p.team && p.swot && p.cost
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
      <div className="flex-1 flex items-center justify-center p-8">
        <EmptyProjectState onCreate={() => createNewProject('My Startup', 'A revolutionary idea')} />
      </div>
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
            onClick={() => createNewProject('New Startup', 'Describe your idea')}
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
              <button className="flex items-center gap-3 p-4 rounded-xl border border-border hover:bg-muted transition-colors text-left">
                <div className="h-10 w-10 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                  <BarChart3 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <span className="text-sm font-medium text-foreground block">View Analytics</span>
                  <span className="text-xs text-muted-foreground">Portfolio insights</span>
                </div>
              </button>
              <button className="flex items-center gap-3 p-4 rounded-xl border border-border hover:bg-muted transition-colors text-left">
                <div className="h-10 w-10 rounded-xl bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
                  <Users className="h-5 w-5 text-violet-600 dark:text-violet-400" />
                </div>
                <div>
                  <span className="text-sm font-medium text-foreground block">Team Review</span>
                  <span className="text-xs text-muted-foreground">Organization planning</span>
                </div>
              </button>
              <button className="flex items-center gap-3 p-4 rounded-xl border border-border hover:bg-muted transition-colors text-left">
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
    </div>
  );
}
