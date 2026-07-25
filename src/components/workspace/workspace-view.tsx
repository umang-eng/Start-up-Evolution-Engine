'use client';

import React, { useState } from 'react';
import { useBlueprintStore } from '@/store/use-blueprint-store';
import { usePipelineStore } from '@/store/use-pipeline-store';
import { cn } from '@/lib/utils';
import { 
  Sparkles, 
  ArrowRight, 
  Play, 
  RefreshCw,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Loader2,
  CheckCircle,
  AlertTriangle,
  Clock,
  Zap,
  Eye,
  EyeOff
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PipelineProgress } from '@/components/pipeline/pipeline-progress';
import { StageName, STAGE_LABELS } from '@/types/blueprint';

const STAGE_ORDER: StageName[] = [
  'dna-analyzer', 'feature-extractor', 'roadmap', 'team-structure',
  'swot', 'cost-estimator', 'final-blueprint',
  'legal-compliance', 'competitive-moat', 'stress-test',
  'financial-intelligence', 'investment-committee', 'product-execution', 'global-expansion',
];

interface WorkspaceViewProps {
  activeProject: any;
  activeStage: StageName;
  onStageSelect: (stage: StageName) => void;
  onStartGeneration: (projectId: string, stage: string) => void;
  onStartCompletePipeline: (projectId: string) => void;
  isGenerating: boolean;
  children: React.ReactNode;
}

export function WorkspaceView({
  activeProject,
  activeStage,
  onStageSelect,
  onStartGeneration,
  onStartCompletePipeline,
  isGenerating,
  children,
}: WorkspaceViewProps) {
  const pipeline = usePipelineStore((s) => s.activePipelines[activeProject?.id]);
  const [showAllStages, setShowAllStages] = useState(false);

  if (!activeProject) return null;

  const completedStages = STAGE_ORDER.filter((stage) => {
    const checkMap: Record<string, () => boolean> = {
      'dna-analyzer': () => !!activeProject.dna,
      'feature-extractor': () => !!activeProject.features,
      'roadmap': () => !!activeProject.roadmap,
      'team-structure': () => !!activeProject.team,
      'swot': () => !!activeProject.swot,
      'cost-estimator': () => !!activeProject.cost,
      'final-blueprint': () => !!activeProject.blueprintCompiled,
      'legal-compliance': () => !!activeProject.legalCompliance,
      'competitive-moat': () => !!activeProject.competitiveMoat,
      'stress-test': () => !!activeProject.stressTest,
      'financial-intelligence': () => !!activeProject.financialIntelligence,
      'investment-committee': () => !!activeProject.investmentCommittee,
      'product-execution': () => !!activeProject.productExecution,
      'global-expansion': () => !!activeProject.globalExpansion,
    };
    return checkMap[stage]?.() ?? false;
  });

  const isPipelineRunning = pipeline?.status === 'running';
  const hasResults = completedStages.length > 0;
  const canGenerateComplete = !isPipelineRunning && activeProject.status !== 'generating';

  return (
    <div className="h-full flex flex-col">
      {/* Workspace Header */}
      <div className="shrink-0 border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="text-lg font-bold text-primary">
                {activeProject.name.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-foreground">{activeProject.name}</h1>
              <p className="text-xs text-muted-foreground">
                {completedStages.length} of {STAGE_ORDER.length} stages completed
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Pipeline Progress Indicator */}
            {isPipelineRunning && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 text-primary animate-spin" />
                <span>Processing...</span>
              </div>
            )}

            {/* Primary CTA */}
            <Button
              onClick={() => onStartCompletePipeline(activeProject.id)}
              disabled={!canGenerateComplete}
              className="gap-2"
            >
              {isGenerating || isPipelineRunning ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Generating...</span>
                </>
              ) : hasResults ? (
                <>
                  <RefreshCw className="h-4 w-4" />
                  <span>Regenerate All</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Generate Complete Blueprint</span>
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Pipeline Progress Bar (when running) */}
        {isPipelineRunning && (
          <div className="mt-4">
            <PipelineProgress projectId={activeProject.id} compact />
          </div>
        )}
      </div>

      {/* Workspace Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto p-6 space-y-6">
          {/* Quick Stage Access */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground">Pipeline Stages</h2>
              <button
                onClick={() => setShowAllStages(!showAllStages)}
                className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
              >
                {showAllStages ? (
                  <>
                    <EyeOff className="h-3 w-3" />
                    Show less
                  </>
                ) : (
                  <>
                    <Eye className="h-3 w-3" />
                    Show all
                  </>
                )}
              </button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
              {(showAllStages ? STAGE_ORDER : STAGE_ORDER.slice(0, 7)).map((stage) => {
                const isCompleted = completedStages.includes(stage);
                const isCurrent = activeStage === stage;
                const stageStatus = pipeline?.stages[stage.replace('-', '_')]?.status;
                const isRunning = stageStatus === 'running';
                const isFailed = stageStatus === 'failed';

                return (
                  <button
                    key={stage}
                    onClick={() => onStageSelect(stage)}
                    className={cn(
                      'flex flex-col items-center gap-2 p-3 rounded-xl border transition-all text-center',
                      isCurrent
                        ? 'border-primary bg-primary/5 shadow-sm'
                        : isCompleted
                        ? 'border-emerald-200 bg-emerald-50/50 dark:border-emerald-800 dark:bg-emerald-900/10'
                        : 'border-border bg-card hover:bg-muted/50',
                      isFailed && 'border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-900/10'
                    )}
                  >
                    <div className={cn(
                      'h-8 w-8 rounded-lg flex items-center justify-center',
                      isCurrent ? 'bg-primary text-primary-foreground' :
                      isCompleted ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400' :
                      isRunning ? 'bg-primary/10 text-primary' :
                      isFailed ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' :
                      'bg-muted text-muted-foreground'
                    )}>
                      {isCompleted ? (
                        <CheckCircle className="h-4 w-4" />
                      ) : isRunning ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : isFailed ? (
                        <AlertTriangle className="h-4 w-4" />
                      ) : (
                        <Clock className="h-4 w-4" />
                      )}
                    </div>
                    <span className="text-[11px] font-medium text-foreground leading-tight">
                      {STAGE_LABELS[stage] || stage}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Stage Content Area */}
          <div className="min-h-[400px]">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
