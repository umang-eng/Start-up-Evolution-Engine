'use client';

import React, { useEffect, useRef, useState } from 'react';
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

const STAGE_ORDER = [
  'dna', 'features', 'roadmap', 'team', 'swot', 'cost', 'legal_compliance',
  'competitive_moat', 'stress_test', 'financial_intelligence',
  'investment_committee', 'product_execution', 'global_expansion', 'blueprint',
];

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
  const progressRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!pipelineStartTime || pipelineStatus !== 'running') return;

    const interval = setInterval(() => {
      setElapsed(Date.now() - pipelineStartTime);
    }, 1000);

    return () => clearInterval(interval);
  }, [pipelineStatus, pipelineStartTime]);

  useEffect(() => {
    if (!compact || !isExpanded) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (!progressRef.current?.contains(event.target as Node)) {
        setIsExpanded(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsExpanded(false);
    };

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [compact, isExpanded]);

  if (!pipeline || pipeline.status === 'idle') return null;

  const stages = Object.values(pipeline.stages);
  const completedCount = stages.filter((s) => s.status === 'completed').length;
  const runningCount = stages.filter((s) => s.status === 'running').length;
  const failedCount = stages.filter((s) => s.status === 'failed').length;
  const totalCount = stages.length;
  const processedCount = completedCount + failedCount;
  const progress = totalCount > 0 ? (processedCount / totalCount) * 100 : 0;
  const completedDurations = stages
    .filter((stage) => stage.status === 'completed' && stage.startTime && stage.endTime)
    .map((stage) => {
      if (stage.startTime === undefined || stage.endTime === undefined) return null;
      return Math.max(0, stage.endTime - stage.startTime);
    })
    .filter((duration): duration is number => duration !== null);
  const averageStageDuration = completedDurations.length > 0
    ? completedDurations.reduce((total, duration) => total + duration, 0) / completedDurations.length
    : null;
  const queuedCount = stages.filter((stage) => stage.status === 'queued').length;
  const runningStage = stages.find((stage) => stage.status === 'running');
  const runningStageIndex = runningStage ? STAGE_ORDER.indexOf(runningStage.stage) : -1;
  const runningStageElapsed = runningStage?.startTime && pipelineStartTime
    ? Math.max(0, elapsed - (runningStage.startTime - pipelineStartTime))
    : 0;
  const eta = averageStageDuration === null
    ? null
    : (runningStage ? Math.max(0, averageStageDuration - runningStageElapsed) : 0)
      + queuedCount * averageStageDuration;

  return (
    <div
      className={cn(
        compact && 'relative z-20 min-h-[66px]',
        compact && isExpanded && 'z-40'
      )}
    >
    <Card
      ref={progressRef}
      className={cn(
        'border-border',
        compact && isExpanded && 'absolute right-0 top-0 z-30 w-[min(32rem,calc(100vw-2rem))] max-w-full bg-card/95 shadow-xl backdrop-blur-md'
      )}
    >
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
              <Badge variant="outline" size="sm" title="Estimate is based on completed stage durations">
                {eta === null
                  ? 'ETA after first stage'
                  : eta > 0
                    ? `~${formatTime(eta)} remaining`
                    : 'Finishing up…'}
              </Badge>
            )}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              aria-label={isExpanded ? 'Collapse pipeline progress' : 'Expand pipeline progress'}
              aria-expanded={isExpanded}
              className="rounded p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className={cn(
          'space-y-4',
          compact && 'max-h-[min(55vh,320px)] overflow-y-auto'
        )}>
          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">
                {runningStage && runningStageIndex >= 0
                  ? `Stage ${runningStageIndex + 1} of ${STAGE_ORDER.length}: ${STAGE_LABELS[runningStage.stage] || runningStage.stage}`
                  : `${processedCount} of ${totalCount} stages completed`}
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
    </div>
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
