'use client';

import React, { useEffect, useState } from 'react';
import { usePipelineStore, PipelineStageProgress, PipelineStageStatus } from '@/store/use-pipeline-store';
import { cn } from '@/lib/utils';
import { 
  CheckCircle, 
  Loader2, 
  Clock, 
  AlertTriangle, 
  Zap,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ProgressBar } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';

const STAGE_LABELS: Record<string, string> = {
  dna: 'DNA Analyzer',
  features: 'Feature Extractor',
  roadmap: 'Roadmap Generator',
  team: 'Team Structure',
  swot: 'SWOT Analysis',
  cost: 'Cost Estimator',
  blueprint: 'Final Blueprint',
  legal_compliance: 'Legal & Compliance',
  competitive_moat: 'Competitive Moat',
  stress_test: 'Stress Test',
  financial_intelligence: 'Financial Intelligence',
  investment_committee: 'Investment Committee',
  product_execution: 'Product Execution',
  global_expansion: 'Global Expansion',
};

const STATUS_CONFIG: Record<PipelineStageStatus, { icon: React.ComponentType<any>; color: string; label: string }> = {
  queued: { icon: Clock, color: 'text-muted-foreground bg-muted', label: 'Queued' },
  running: { icon: Loader2, color: 'text-primary bg-primary/10', label: 'Running' },
  completed: { icon: CheckCircle, color: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/20', label: 'Done' },
  failed: { icon: AlertTriangle, color: 'text-red-500 bg-red-50 dark:bg-red-900/20', label: 'Failed' },
  cached: { icon: Zap, color: 'text-amber-500 bg-amber-50 dark:bg-amber-900/20', label: 'Cached' },
};

interface PipelineProgressProps {
  projectId: string;
  compact?: boolean;
}

export function PipelineProgress({ projectId, compact = false }: PipelineProgressProps) {
  const pipeline = usePipelineStore((s) => s.activePipelines[projectId]);
  const pipelineStatus = pipeline?.status;
  const pipelineStartTime = pipeline?.startTime;
  const [elapsed, setElapsed] = useState(0);
  const [isExpanded, setIsExpanded] = useState(!compact);

  useEffect(() => {
    if (!pipelineStartTime || pipelineStatus !== 'running') return;

    const interval = setInterval(() => {
      setElapsed(Date.now() - pipelineStartTime);
    }, 1000);

    return () => clearInterval(interval);
  }, [pipelineStatus, pipelineStartTime]);

  if (!pipeline || pipeline.status === 'idle') return null;

  const stages = Object.values(pipeline.stages);
  const completedCount = stages.filter((s) => s.status === 'completed').length;
  const runningCount = stages.filter((s) => s.status === 'running').length;
  const failedCount = stages.filter((s) => s.status === 'failed').length;
  const totalCount = stages.length;
  const processedCount = completedCount + failedCount;
  const progress = totalCount > 0 ? (processedCount / totalCount) * 100 : 0;
  const averageStageDuration = processedCount > 0 ? elapsed / processedCount : null;
  const queuedCount = stages.filter((stage) => stage.status === 'queued').length;
  const runningStage = stages.find((stage) => stage.status === 'running');
  const runningStageElapsed = runningStage?.startTime && pipelineStartTime
    ? Math.max(0, elapsed - (runningStage.startTime - pipelineStartTime))
    : 0;
  const eta = averageStageDuration === null
    ? null
    : Math.max(0, averageStageDuration - runningStageElapsed) + queuedCount * averageStageDuration;

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-foreground flex items-center gap-2">
            {pipeline.status === 'running' && (
              <Loader2 className="h-4 w-4 text-primary animate-spin" />
            )}
            {pipeline.status === 'completed' && (
              <CheckCircle className="h-4 w-4 text-emerald-500" />
            )}
            {pipeline.status === 'failed' && (
              <AlertTriangle className="h-4 w-4 text-red-500" />
            )}
            Pipeline Progress
          </CardTitle>
          <div className="flex items-center gap-2">
            {pipeline.status === 'running' && (
              <Badge variant="secondary" size="sm">
                {formatTime(elapsed)} elapsed
              </Badge>
            )}
            {pipeline.status === 'running' && (
              <Badge variant="outline" size="sm" title="Estimated from completed stage durations; it updates as stages finish">
                {eta === null ? 'Estimating completion…' : eta > 0 ? `~${formatTime(eta)} remaining` : 'Finishing up…'}
              </Badge>
            )}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-muted-foreground hover:text-foreground"
            >
              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-4">
          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">
                {processedCount} of {totalCount} stages
              </span>
              <span className="font-medium text-foreground">{Math.round(progress)}%</span>
            </div>
            <ProgressBar value={progress} size="md" />
          </div>

          {/* Stage Stats */}
          <div className="flex items-center gap-4 text-xs">
            {runningCount > 0 && (
              <div className="flex items-center gap-1.5 text-primary">
                <Loader2 className="h-3 w-3 animate-spin" />
                <span>{runningCount} running</span>
              </div>
            )}
            {completedCount > 0 && (
              <div className="flex items-center gap-1.5 text-emerald-500">
                <CheckCircle className="h-3 w-3" />
                <span>{completedCount} completed</span>
              </div>
            )}
            {failedCount > 0 && (
              <div className="flex items-center gap-1.5 text-red-500">
                <AlertTriangle className="h-3 w-3" />
                <span>{failedCount} failed</span>
              </div>
            )}
          </div>

          {/* Stage List */}
          <div className="space-y-1.5">
            {stages.map((stage) => (
              <StageItem key={stage.stage} stage={stage} />
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

function StageItem({ stage }: { stage: PipelineStageProgress }) {
  const config = STATUS_CONFIG[stage.status];
  const Icon = config.icon;
  const label = STAGE_LABELS[stage.stage] || stage.stage;
  const duration = stage.endTime && stage.startTime ? stage.endTime - stage.startTime : null;

  return (
    <div className="flex items-center gap-3 py-2 px-3 rounded-lg bg-muted/50 text-sm">
      <div className={cn('h-6 w-6 rounded-md flex items-center justify-center', config.color)}>
        <Icon className={cn('h-3.5 w-3.5', stage.status === 'running' && 'animate-spin')} />
      </div>
      <span className="flex-1 text-foreground">{label}</span>
      {stage.error && (
        <span className="max-w-[45%] truncate text-xs text-red-600" title={stage.error}>
          {stage.error}
        </span>
      )}
      {duration !== null && (
        <span className="text-xs text-muted-foreground">{formatTime(duration)}</span>
      )}
      <Badge variant="ghost" size="sm">{config.label}</Badge>
    </div>
  );
}

function formatTime(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (minutes > 0) return `${minutes}m ${secs}s`;
  return `${secs}s`;
}
