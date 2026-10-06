'use client';

import React, { useState, useEffect, useTransition, useCallback, useRef } from 'react';
import { useBlueprintStore } from '@/store/use-blueprint-store';
import { useAuth } from '@/components/shared/auth-provider';
import { useNotificationStore } from '@/store/use-notification-store';
import { usePipelineStore } from '@/store/use-pipeline-store';
import { 
  api, getAccessToken, 
  mapDnaResponse, mapFeaturesResponse, mapRoadmapResponse, mapTeamResponse, 
  mapSwotResponse, mapCostResponse,
  mapLegalComplianceResponse, mapCompetitiveMoatResponse, mapStressTestResponse,
  mapFinancialIntelligenceResponse, mapInvestmentCommitteeResponse,
  mapProductExecutionResponse, mapGlobalExpansionResponse
} from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { useSettingsStore } from '@/store/use-settings-store';
import { Sidebar } from '@/components/shared/sidebar';
import { Navbar } from '@/components/shared/navbar';
import { GlassPanel } from '@/components/shared/glass-panel';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ExecutiveDashboard } from '@/components/dashboard/executive-dashboard';
import { WorkspaceView } from '@/components/workspace';
import { PipelineProgress } from '@/components/pipeline/pipeline-progress';
import { NotificationPanel } from '@/components/notifications/notification-panel';
import { requestNotificationPermission } from '@/components/notifications/notification-panel';
import { 
  Sparkles, 
  ArrowRight, 
  Play, 
  RefreshCw, 
  CheckCircle, 
  AlertTriangle,
  Dna,
  GitBranch,
  LineChart,
  Network,
  TrendingUp,
  Award,
  ScrollText,
  Plus,
  Shield,
  Target,
  Zap,
  BarChart3,
  Users,
  Rocket,
  Globe,
  ChevronLeft,
  ChevronRight,
  Loader2
} from 'lucide-react';
import { StageName, ALL_STAGES, STAGE_LABELS } from '@/types/blueprint';

function formatInvestmentRecommendation(value: unknown): string {
  if (typeof value === 'string') return value;
  if (!value || typeof value !== 'object' || Array.isArray(value)) return '';

  const recommendation = value as Record<string, unknown>;
  return [recommendation.recommendation, recommendation.investment_thesis]
    .filter((part): part is string => typeof part === 'string' && part.length > 0)
    .join(' — ');
}

const STAGE_ORDER: StageName[] = [
  'dna-analyzer',
  'feature-extractor',
  'roadmap',
  'team-structure',
  'swot',
  'cost-estimator',
  'legal-compliance',
  'competitive-moat',
  'stress-test',
  'financial-intelligence',
  'investment-committee',
  'product-execution',
  'global-expansion',
  'final-blueprint',
];

const STAGE_ICONS: Record<StageName, any> = {
  'dna-analyzer': Dna,
  'feature-extractor': GitBranch,
  'roadmap': LineChart,
  'team-structure': Network,
  'swot': TrendingUp,
  'cost-estimator': Award,
  'final-blueprint': ScrollText,
  'legal-compliance': Shield,
  'competitive-moat': Target,
  'stress-test': Zap,
  'financial-intelligence': BarChart3,
  'investment-committee': Users,
  'product-execution': Rocket,
  'global-expansion': Globe,
};

const getBackendStageName = (frontendStage: string): string => {
  const mapping: Record<string, string> = {
    'dna-analyzer': 'dna',
    'feature-extractor': 'features',
    'roadmap': 'roadmap',
    'team-structure': 'team',
    'swot': 'swot',
    'cost-estimator': 'cost',
    'final-blueprint': 'blueprint',
    'legal-compliance': 'legal_compliance',
    'competitive-moat': 'competitive_moat',
    'stress-test': 'stress_test',
    'financial-intelligence': 'financial_intelligence',
    'investment-committee': 'investment_committee',
    'product-execution': 'product_execution',
    'global-expansion': 'global_expansion',
  };
  return mapping[frontendStage] || 'dna';
};

const getFrontendStageName = (backendStage: string): StageName => {
  const mapping: Record<string, StageName> = {
    'dna': 'dna-analyzer',
    'features': 'feature-extractor',
    'roadmap': 'roadmap',
    'team': 'team-structure',
    'swot': 'swot',
    'cost': 'cost-estimator',
    'blueprint': 'final-blueprint',
    'legal_compliance': 'legal-compliance',
    'competitive_moat': 'competitive-moat',
    'stress_test': 'stress-test',
    'financial_intelligence': 'financial-intelligence',
    'investment_committee': 'investment-committee',
    'product_execution': 'product-execution',
    'global_expansion': 'global-expansion',
  };
  return mapping[backendStage] || 'dna-analyzer';
};

const isStageCompleted = (stage: StageName, project: any): boolean => {
  const checkMap: Record<StageName, () => boolean> = {
    'dna-analyzer': () => !!project.dna,
    'feature-extractor': () => !!project.features,
    'roadmap': () => !!project.roadmap,
    'team-structure': () => !!project.team,
    'swot': () => !!project.swot,
    'cost-estimator': () => !!project.cost,
    'final-blueprint': () => !!project.blueprintCompiled,
    'legal-compliance': () => !!project.legalCompliance,
    'competitive-moat': () => !!project.competitiveMoat,
    'stress-test': () => !!project.stressTest,
    'financial-intelligence': () => !!project.financialIntelligence,
    'investment-committee': () => !!project.investmentCommittee,
    'product-execution': () => !!project.productExecution,
    'global-expansion': () => !!project.globalExpansion,
  };
  return checkMap[stage]?.() ?? false;
};

const PIPELINE_STAGE_ORDER: StageName[] = [
  'dna-analyzer', 'feature-extractor', 'roadmap', 'team-structure',
  'swot', 'cost-estimator', 'legal-compliance',
  'competitive-moat', 'stress-test', 'financial-intelligence',
  'investment-committee', 'product-execution', 'global-expansion',
  'final-blueprint',
];

const isStageUnlocked = (stage: StageName, project: any): boolean => {
  const index = PIPELINE_STAGE_ORDER.indexOf(stage);
  return index <= 0 || PIPELINE_STAGE_ORDER
    .slice(0, index)
    .every((previousStage) => isStageCompleted(previousStage, project));
};

export default function WorkspacePage() {
  const { 
    projects, 
    activeProjectId, 
    activeStage,
    setActiveStage,
    loadProjects,
    createNewProject,
    updateProjectStatus,
    updateProjectStage,
    loadBlueprint,
    saveDNA,
    saveFeatures,
    saveRoadmap,
    saveTeam,
    saveSWOT,
    saveCost,
    saveLegalCompliance,
    saveCompetitiveMoat,
    saveStressTest,
    saveFinancialIntelligence,
    saveInvestmentCommittee,
    saveProductExecution,
    saveGlobalExpansion,
    completeBlueprint
  } = useBlueprintStore();

  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [inputVal, setInputVal] = useState('');
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<'model' | 'target' | 'usp'>('model');
  const [selectedScenario, setSelectedScenario] = useState<'lean' | 'balanced' | 'aggressive'>('lean');
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [isPending, startTransition] = useTransition();
  const activeEventSources = useRef<Record<string, EventSource>>({});
  const activeSessionIds = useRef<Record<string, string | undefined>>({});
  const activeStatusPolls = useRef<Record<string, ReturnType<typeof setInterval>>>({});
  const pendingGenerationProjects = useRef(new Set<string>());

  const clearGenerationStatusPoll = (projectId: string) => {
    const timer = activeStatusPolls.current[projectId];
    if (!timer) return;
    clearInterval(timer);
    delete activeStatusPolls.current[projectId];
  };

  const activeProject = projects.find(p => p.id === activeProjectId);
  const handleStageSelect = (stage: StageName) => {
    if (activeProject && isStageUnlocked(stage, activeProject)) {
      setActiveStage(stage);
    }
  };
  const { currencySymbol, costBuffer } = useSettingsStore();

  const formatCost = (amount: number) => {
    const paddedAmount = amount * (1 + (costBuffer || 0) / 100);
    return `${currencySymbol || '$'}${Math.round(paddedAmount).toLocaleString()}`;
  };

  const handleDownloadBlueprintPdf = async (projectId: string) => {
    const previewWindow = window.open('', '_blank');
    setIsExportingPdf(true);
    try {
      const response = await fetch(api.exports.pdf(projectId));
      if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.detail || `PDF export failed (${response.status}).`);
      }
      const pdf = await response.blob();
      if (pdf.type !== 'application/pdf' || pdf.size < 5) {
        throw new Error('The server response was not a valid PDF document.');
      }
      const signature = new Uint8Array(await pdf.slice(0, 5).arrayBuffer());
      if (new TextDecoder().decode(signature) !== '%PDF-') {
        throw new Error('The generated file is not a valid PDF.');
      }

      const previewUrl = URL.createObjectURL(pdf);
      const anchor = document.createElement('a');
      anchor.href = previewUrl;
      anchor.download = `blueprint-${projectId}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      if (previewWindow) previewWindow.location.replace(previewUrl);
      window.setTimeout(() => URL.revokeObjectURL(previewUrl), 60_000);
    } catch (error) {
      previewWindow?.close();
      const message = error instanceof Error ? error.message : 'Unable to generate the PDF.';
      window.alert(message);
    } finally {
      setIsExportingPdf(false);
    }
  };

  // Load projects from database on startup
  useEffect(() => {
    if (isAuthenticated) {
      loadProjects();
    }
  }, [isAuthenticated]);

  // Load compiled details or partial results if active project state is not yet loaded in store
  useEffect(() => {
    if (activeProject && !activeProject.dna && activeProjectId) {
      loadBlueprint(activeProjectId);
    }
  }, [activeProjectId]);

  // Development fallback: keep the UI current when Redis/SSE is unavailable.
  useEffect(() => {
    if (!activeProjectId || activeProject?.status !== 'generating') return;
    const timer = window.setInterval(() => {
      loadBlueprint(activeProjectId);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [activeProjectId, activeProject?.status, loadBlueprint]);

  // AI-powered idea enhancement using the configured analysis provider
  const handleEnhance = async () => {
    if (!inputVal.trim()) return;
    setIsEnhancing(true);
    try {
      const result = await api.generator.enhance(inputVal.trim());
      if (result?.enhanced_idea) {
        setInputVal(result.enhanced_idea);
      }
    } catch (err: any) {
      console.error('Idea enhancement failed:', err);
      // Fallback: append strategic context if API fails
      setInputVal(prev => prev + ' — targeting early adopters via a SaaS subscription model with freemium onboarding and usage-based pricing.');
    } finally {
      setIsEnhancing(false);
    }
  };

  // Run real generation sequence using Server-Sent Events (SSE)
  const handleStartGeneration = async (
    projId: string,
    stage?: string,
    startFromStage?: string,
  ) => {
    if (pendingGenerationProjects.current.has(projId)) return;
    pendingGenerationProjects.current.add(projId);

    if (stage) {
      setActiveStage(getFrontendStageName(stage));
    }
    updateProjectStatus(projId, 'generating');
    usePipelineStore.getState().beginPipeline(projId, stage, startFromStage);
    setStreamLog([stage
      ? `Contacting intelligence orchestrator for stage [${stage.toUpperCase()}]...`
      : 'Contacting intelligence orchestrator for the complete blueprint...']);

    const token = getAccessToken();
    if (!token) {
      setStreamLog(prev => ["❌ Error: Authentication credentials missing. Please log in again.", ...prev]);
      updateProjectStatus(projId, 'error');
      usePipelineStore.getState().finishPipeline(projId, 'failed');
      pendingGenerationProjects.current.delete(projId);
      return;
    }

    try {
      const provider = await api.generator.providerStatus();
      setStreamLog(prev => [
        `✅ Inference provider ready (${provider.model}).`,
        ...prev,
      ]);

      // 1. Trigger Async execution run
      const runResponse = await api.generator.run(projId, stage, startFromStage);
      const sessionId = runResponse?.session_id ?? runResponse?.data?.session_id;
      setStreamLog(prev => ["✅ Generation pipeline triggered. Opening stream connection...", ...prev]);

      // 2. Open EventSource connection with token query param
      const eventSourceUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/streams/progress/${projId}?token=${encodeURIComponent(token)}`;
      const es = new EventSource(eventSourceUrl);
      activeEventSources.current[projId] = es;
      activeSessionIds.current[projId] = sessionId;
      let statusCheckInFlight = false;
      activeStatusPolls.current[projId] = setInterval(async () => {
        if (statusCheckInFlight) return;
        statusCheckInFlight = true;
        try {
          const runStatus = await api.generator.status(projId);
          if (runStatus.session_id !== sessionId) return;

          if (runStatus.status === 'RUNNING' && runStatus.current_stage && runStatus.current_stage !== 'queued') {
            const currentPipeline = usePipelineStore.getState().activePipelines[projId];
            if (currentPipeline?.stages[runStatus.current_stage]?.status !== 'running') {
              usePipelineStore.getState().updateStage(projId, runStatus.current_stage, {
                status: 'running',
                startTime: Date.now(),
              });
            }
          } else if (runStatus.status === 'COMPLETED') {
            clearGenerationStatusPoll(projId);
            es.close();
            updateProjectStatus(projId, stage ? 'idle' : 'completed');
            usePipelineStore.getState().finishPipeline(projId, 'completed');
            delete activeEventSources.current[projId];
            delete activeSessionIds.current[projId];
            pendingGenerationProjects.current.delete(projId);
            setStreamLog(prev => ['🎉 Generation completed. Results restored from the server.', ...prev]);
            void loadBlueprint(projId);
          } else if (['FAILED', 'ENQUEUE_FAILED', 'CANCELLED'].includes(runStatus.status)) {
            clearGenerationStatusPoll(projId);
            es.close();
            const message = runStatus.error_message
              || (runStatus.status === 'CANCELLED' ? 'Generation was cancelled.' : 'Generation failed.');
            const pipeline = usePipelineStore.getState().activePipelines[projId];
            const runningStage = Object.values(pipeline?.stages || {})
              .find((pipelineStage) => pipelineStage.status === 'running')?.stage;
            if (runningStage) {
              usePipelineStore.getState().updateStage(projId, runningStage, {
                status: 'failed',
                error: message,
                endTime: Date.now(),
              });
            }
            updateProjectStatus(projId, runStatus.status === 'CANCELLED' ? 'idle' : 'error');
            usePipelineStore.getState().finishPipeline(projId, 'failed');
            delete activeEventSources.current[projId];
            delete activeSessionIds.current[projId];
            pendingGenerationProjects.current.delete(projId);
            setStreamLog(prev => [`❌ ${message}`, ...prev]);
            useNotificationStore.getState().addNotification({
              title: runStatus.status === 'CANCELLED' ? 'Generation Stopped' : 'Pipeline Failed',
              message,
              type: runStatus.status === 'CANCELLED' ? 'warning' : 'error',
            });
          }
        } catch (err) {
          console.warn('Could not refresh generation status; will retry.', err);
        } finally {
          statusCheckInFlight = false;
        }
      }, 15000);
      let consecutiveErrors = 0;
      const MAX_ERRORS = 5;

      es.addEventListener('system:init', () => {
        consecutiveErrors = 0;
        setStreamLog(prev => ["🔗 Stream channel established.", ...prev]);
      });

      es.addEventListener('workflow:started', () => {
        setStreamLog(prev => ["🚀 Pipeline running — evolving startup DNA architecture...", ...prev]);
      });

      es.addEventListener('module:started', (e: any) => {
        try {
          const data = JSON.parse(e.data);
          const stageName = data.module_info?.module_name || '';
          if (stageName) {
            updateProjectStage(projId, getFrontendStageName(stageName));
            usePipelineStore.getState().updateStage(projId, stageName, {
              status: 'running',
              startTime: Date.now(),
            });
          }
          setStreamLog(prev => [`⚙️ Stage [${stageName.toUpperCase()}]: compiling dataset...`, ...prev]);
        } catch (err) {
          console.error('module:started parse error', err);
        }
      });

      es.addEventListener('module:completed', (e: any) => {
        try {
          const data = JSON.parse(e.data);
          const stageName = data.module_info?.module_name;
          const result = data.result_info;

          if (stageName) {
            usePipelineStore.getState().updateStage(projId, stageName, {
              status: 'completed',
              endTime: Date.now(),
            });
          }
          setStreamLog(prev => [`✅ Stage [${stageName?.toUpperCase()}] compiled successfully.`, ...prev]);

          // Save partial result structures into Zustand store in real-time
          if (stageName === 'dna') saveDNA(projId, mapDnaResponse(result));
          else if (stageName === 'features') saveFeatures(projId, mapFeaturesResponse(result));
          else if (stageName === 'roadmap') saveRoadmap(projId, mapRoadmapResponse(result));
          else if (stageName === 'team') saveTeam(projId, mapTeamResponse(result));
          else if (stageName === 'swot') saveSWOT(projId, mapSwotResponse(result, {
            idea: activeProject?.ideaPrompt,
          }));
          else if (stageName === 'cost') saveCost(projId, mapCostResponse(result, {
            features: activeProject?.features,
            team: activeProject?.team,
          }));
          else if (stageName === 'blueprint') {
            // Blueprint completion is persisted as a unified record. Reload it
            // so the compiled flag and all derived stage state update together.
            completeBlueprint(projId);
            void loadBlueprint(projId);
          }
          else if (stageName === 'legal_compliance') saveLegalCompliance(projId, mapLegalComplianceResponse(result));
          else if (stageName === 'competitive_moat') saveCompetitiveMoat(projId, mapCompetitiveMoatResponse(result));
          else if (stageName === 'stress_test') saveStressTest(projId, mapStressTestResponse(result));
          else if (stageName === 'financial_intelligence') saveFinancialIntelligence(projId, mapFinancialIntelligenceResponse(result));
          else if (stageName === 'investment_committee') saveInvestmentCommittee(projId, mapInvestmentCommitteeResponse(result));
          else if (stageName === 'product_execution') saveProductExecution(projId, mapProductExecutionResponse(result));
          else if (stageName === 'global_expansion') saveGlobalExpansion(projId, mapGlobalExpansionResponse(result));
        } catch (err) {
          console.error('module:completed parse error', err);
        }
      });

      es.addEventListener('module:failed', (e: any) => {
        try {
          const data = JSON.parse(e.data);
          const stageName = data.module_info?.module_name;
          const errMsg = data.error_info?.error_message || 'Unknown error';
          const isFatal = data.error_info?.is_fatal;
          if (stageName) {
            usePipelineStore.getState().updateStage(projId, stageName, {
              status: 'failed',
              error: errMsg,
              endTime: Date.now(),
            });
          }
          setStreamLog(prev => [
            `${isFatal ? '❌' : '⚠️'} Stage [${stageName?.toUpperCase()}] ${isFatal ? 'FAILED' : 'warning'}: ${errMsg}`,
            ...prev
          ]);
        } catch (err) {
          console.error('module:failed parse error', err);
        }
      });

      es.addEventListener('workflow:completed', () => {
        clearGenerationStatusPoll(projId);
        const stageLabel = stage ? (stage === 'blueprint' ? 'Final Blueprint' : `Stage [${stage.toUpperCase()}]`) : 'Complete Blueprint';
        setStreamLog(prev => [`🎉 ${stageLabel} compiled successfully!`, ...prev]);
        updateProjectStatus(projId, stage ? 'idle' : 'completed');
        usePipelineStore.getState().finishPipeline(projId, 'completed');
        es.close();
        delete activeEventSources.current[projId];
        delete activeSessionIds.current[projId];
        pendingGenerationProjects.current.delete(projId);
        loadBlueprint(projId);
      });

      es.addEventListener('workflow:failed', (e: any) => {
        clearGenerationStatusPoll(projId);
        try {
          const data = JSON.parse(e.data);
          const errMsg = data.error_info?.error_message || 'Compilation failed';
          setStreamLog(prev => [`❌ Fatal error: ${errMsg}`, ...prev]);
          const pipeline = usePipelineStore.getState().activePipelines[projId];
          const runningStage = Object.values(pipeline?.stages || {})
            .find((pipelineStage) => pipelineStage.status === 'running')?.stage;
          if (runningStage) {
            usePipelineStore.getState().updateStage(projId, runningStage, {
              status: 'failed',
              error: errMsg,
              endTime: Date.now(),
            });
          }
          updateProjectStatus(projId, 'error');
          usePipelineStore.getState().finishPipeline(projId, 'failed');
          es.close();
          delete activeEventSources.current[projId];
          delete activeSessionIds.current[projId];
          pendingGenerationProjects.current.delete(projId);
        } catch (err) {
          console.error('workflow:failed parse error', err);
        }
      });

      es.onerror = (event) => {
        consecutiveErrors++;
        if (consecutiveErrors >= MAX_ERRORS) {
          setStreamLog(prev => ['⚠️ Live updates disconnected. Checking generation status in the background.', ...prev]);
          es.close();
        } else {
          console.warn(`EventSource error #${consecutiveErrors} — retrying...`);
        }
      };

    } catch (err: any) {
      clearGenerationStatusPoll(projId);
      setStreamLog(prev => [`❌ Trigger failed: ${err.message}`, ...prev]);
      updateProjectStatus(projId, 'error');
      usePipelineStore.getState().finishPipeline(projId, 'failed');
      pendingGenerationProjects.current.delete(projId);
    }
  };

  const handleStopGeneration = useCallback(async (projId: string) => {
    activeEventSources.current[projId]?.close();
    clearGenerationStatusPoll(projId);
    delete activeEventSources.current[projId];
    delete activeSessionIds.current[projId];
    pendingGenerationProjects.current.delete(projId);
    try {
      await api.generator.cancel(projId);
      setStreamLog(prev => ['Generation stopped. Completed sections were preserved.', ...prev]);
    } catch (err: any) {
      setStreamLog(prev => [`Could not stop generation: ${err.message}`, ...prev]);
    } finally {
      updateProjectStatus(projId, 'idle');
      usePipelineStore.getState().finishPipeline(projId, 'failed');
    }
  }, [updateProjectStatus]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;

    startTransition(async () => {
      try {
        const projectName = inputVal.trim().split(/\s+/).slice(0, 6).join(' ');
        const p = await createNewProject(
          projectName.length >= 3 ? projectName : `${projectName} Project`,
          inputVal.trim(),
        );
        setInputVal('');
        handleStartGeneration(p.id, 'dna');
      } catch (err) {
        console.error('Failed to evolve startup idea:', err);
      }
    });
  };

  const insertPrompt = (text: string) => {
    setInputVal(text);
  };

  // Handle one-click complete pipeline generation
  const handleStartCompletePipeline = useCallback(async (projectId: string) => {
    const project = projects.find(p => p.id === projectId);
    if (!project) return;

    const firstIncompleteStage = PIPELINE_STAGE_ORDER.find((stage) => !isStageCompleted(stage, project));
    if (!firstIncompleteStage) return;

    updateProjectStatus(projectId, 'generating');
    setActiveStage(firstIncompleteStage);
    setStreamLog(['Starting complete venture blueprint generation...']);
    const startFromStage = getBackendStageName(firstIncompleteStage);
    await handleStartGeneration(projectId, undefined, startFromStage);
  }, [projects, handleStartGeneration, updateProjectStatus]);

  // Request notification permission on mount
  useEffect(() => {
    requestNotificationPermission();
  }, []);

  // Safe loading check
  if (authLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-2">
          <RefreshCw className="h-6 w-6 text-primary animate-spin" />
          <span className="text-sm text-muted-foreground">Authenticating session...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex overflow-hidden bg-background">
      {/* Sidebar Navigation */}
      <Sidebar />

      {/* Main Container Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <Navbar />

        {/* Focus Viewport - Single scrollable area */}
        <main className="flex-1 overflow-y-auto">
          {!activeProject ? (
            /* EXECUTIVE DASHBOARD */
            <ExecutiveDashboard />
          ) : (
            /* UNIFIED WORKSPACE */
            <WorkspaceView
              activeProject={activeProject}
              activeStage={activeStage}
              onStageSelect={handleStageSelect}
              onStartGeneration={handleStartGeneration}
              onStartCompletePipeline={handleStartCompletePipeline}
              onStopGeneration={handleStopGeneration}
              isGenerating={activeProject.status === 'generating'}
            >
              {/* Stage Content */}
              <div className="space-y-6">
                {/* ERROR STATE */}
                {activeProject.status === 'error' && (
                  <Card className="border-red-200 bg-red-50/50 dark:bg-red-900/10 dark:border-red-800/30">
                    <CardHeader>
                      <CardTitle className="text-base font-semibold text-red-700 dark:text-red-400 flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4" />
                        Generation Failed
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm text-red-600 dark:text-red-400/80 leading-relaxed">
                        {streamLog.find((log) => log.startsWith('❌'))?.replace(/^❌\s*/, '')
                          || 'The AI analysis service encountered an error while processing this stage.'}
                        <br /><strong>Check the provider and worker status</strong>, then retry.
                      </p>
                      <div className="flex gap-2">
                        <Button
                          onClick={() => handleStartGeneration(activeProject.id, getBackendStageName(activeStage))}
                          className="gap-1.5 bg-red-600 hover:bg-red-700 text-white"
                        >
                          <Sparkles className="h-4 w-4" />
                          <span>Retry Generation</span>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Generation state skeletons */}
                {activeProject.status === 'generating' && !isStageCompleted(activeStage, activeProject) && (
                  <Card className="border-border">
                    <CardHeader>
                      <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                        {activeStage === 'final-blueprint'
                          ? 'Compiling Final Blueprint...'
                          : `Generating ${STAGE_LABELS[activeStage] || 'Pipeline Stage'}...`}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="skeleton h-4 w-3/4" />
                      <div className="skeleton h-4 w-1/2" />
                      <div className="skeleton h-32 w-full" />
                      <p className="text-sm text-muted-foreground">
                        Working on {STAGE_LABELS[activeStage] || 'the next stage'}. Previously completed stages remain available in the pipeline above.
                      </p>
                    </CardContent>
                  </Card>
                )}


                {/* STAGE: DNA ANALYZER */}
                {activeStage === 'dna-analyzer' && activeProject.dna && (
                  <Card className="border-border">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-xl font-semibold tracking-tight text-foreground">
                        Business DNA Report
                      </CardTitle>
                      <div className="badge-primary gap-1.5">
                        <Dna className="h-4 w-4" />
                        <span>Confidence {activeProject.dna.confidence}%</span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Overview grids */}
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 p-4 rounded-lg bg-muted text-sm">
                        <div>
                          <span className="text-muted-foreground block mb-0.5 text-xs">Category</span>
                          <span className="font-semibold text-foreground">{activeProject.dna.category}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground block mb-0.5 text-xs">Business Model</span>
                          <span className="font-semibold text-foreground">{activeProject.dna.businessModel}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground block mb-0.5 text-xs">Target Market</span>
                          <span className="font-semibold text-foreground">{activeProject.dna.targetMarket}</span>
                        </div>
                      </div>

                      {/* Score metrics */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                        <div className="space-y-3">
                          <span className="text-overline block">
                            Strategic Scores
                          </span>
                          {Object.entries(activeProject.dna.scores).map(([key, val]: any) => (
                            <div key={key} className="flex justify-between items-center text-sm border-b border-border pb-2">
                              <span className="capitalize text-muted-foreground">{key.replace('_', ' ')}</span>
                              <span className="font-semibold text-foreground">{val}/100</span>
                            </div>
                          ))}
                        </div>
                        <div className="h-48 border border-border rounded-lg bg-muted flex items-center justify-center relative overflow-hidden">
                          <div className="h-32 w-32 rounded-full border-2 border-primary/20 flex items-center justify-center">
                            <div className="h-20 w-20 rounded-full border border-primary flex items-center justify-center text-sm font-semibold text-primary bg-card shadow-sm">
                              {Math.round(Object.values(activeProject.dna.scores).reduce((a: any, b: any) => a + b, 0) / 6)} Avg
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Tabs */}
                      <div className="space-y-3">
                        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-full">
                          <TabsList className="bg-muted border border-border">
                            <TabsTrigger value="model" className="text-xs">Value Proposition</TabsTrigger>
                            <TabsTrigger value="target" className="text-xs">USP</TabsTrigger>
                            <TabsTrigger value="usp" className="text-xs">Summary</TabsTrigger>
                          </TabsList>
                          <TabsContent value="model" className="p-4 bg-muted/50 rounded-lg text-sm leading-relaxed text-muted-foreground border border-border">
                            {activeProject.dna.valueProposition}
                          </TabsContent>
                          <TabsContent value="target" className="p-4 bg-muted/50 rounded-lg text-sm leading-relaxed text-muted-foreground border border-border">
                            {activeProject.dna.usp}
                          </TabsContent>
                          <TabsContent value="usp" className="p-4 bg-muted/50 rounded-lg text-sm leading-relaxed text-muted-foreground border border-border">
                            {activeProject.dna.summary}
                          </TabsContent>
                        </Tabs>
                      </div>

                      {/* Handoff CTA */}
                      <div className="pt-4 border-t border-border flex justify-end">
                        <Button 
                          onClick={() => setActiveStage('feature-extractor')}
                          className="gap-1.5"
                        >
                          <span>Proceed to Feature Extraction</span>
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: DNA ANALYZER EMPTY STATE */}
                {activeStage === 'dna-analyzer' && !activeProject.dna && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                  <Card className="border-border p-12 flex flex-col items-center justify-center text-center space-y-6">
                    <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                      <Dna className="h-8 w-8" />
                    </div>
                    <div className="space-y-2 max-w-md">
                      <h3 className="text-xl font-semibold text-foreground">Business DNA Analyzer</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        Evaluate market viability, validate user demographics, map value propositions, and outline key competitive advantages for your concept.
                      </p>
                    </div>
                    <Button 
                      onClick={() => handleStartGeneration(activeProject.id, 'dna')}
                      className="gap-2 px-6"
                    >
                      <Sparkles className="h-4 w-4" />
                      <span>Analyze Concept DNA</span>
                    </Button>
                  </Card>
                )}

                {/* STAGE: FEATURE EXTRACTOR */}
                {activeStage === 'feature-extractor' && activeProject.features && (
                  <Card className="border-border">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold tracking-tight text-foreground">
                        Feature Architecture Spec
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid grid-cols-3 gap-4 text-center p-4 bg-muted rounded-lg">
                        <div>
                          <span className="text-xs text-muted-foreground block">Total Features</span>
                          <span className="text-lg font-bold text-foreground">{activeProject.features.totalFeatures}</span>
                        </div>
                        <div>
                          <span className="text-xs text-muted-foreground block">MVP Selected</span>
                          <span className="text-lg font-bold text-primary">{activeProject.features.mvpFeatureIds.length}</span>
                        </div>
                        <div>
                          <span className="text-xs text-muted-foreground block">Complexity</span>
                          <span className="text-lg font-bold text-foreground capitalize">{activeProject.features.complexityScore}</span>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <span className="text-overline block">
                          Extracted Features
                        </span>
                        <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                          {activeProject.features.features.map((feature: any) => (
                            <div key={feature.id} className="p-3 rounded-lg border border-border bg-card flex items-center justify-between hover:bg-muted/50 transition-colors">
                              <div>
                                <span className="text-sm font-medium text-foreground block">{feature.name}</span>
                                <span className="text-xs text-muted-foreground leading-relaxed">{feature.description}</span>
                              </div>
                              <span className="badge-default text-[10px]">
                                {feature.priority}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Handoff CTA */}
                      <div className="pt-4 border-t border-border flex justify-end">
                        <Button 
                          onClick={() => setActiveStage('roadmap')}
                          className="gap-1.5"
                        >
                          <span>Generate Timeline Roadmap</span>
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: FEATURE EXTRACTOR EMPTY STATE */}
                {activeStage === 'feature-extractor' && !activeProject.features && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                  <Card className="border-border p-12 flex flex-col items-center justify-center text-center space-y-6">
                    <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                      <GitBranch className="h-8 w-8" />
                    </div>
                    <div className="space-y-2 max-w-md">
                      <h3 className="text-xl font-semibold text-foreground">Technical Feature Extractor</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        Convert your business DNA into a structured PRD, feature lists, and MVP scoped items.
                      </p>
                    </div>
                    <Button 
                      onClick={() => handleStartGeneration(activeProject.id, 'features')}
                      className="gap-2 px-6"
                    >
                      <Sparkles className="h-4 w-4" />
                      <span>Extract MVP Features</span>
                    </Button>
                  </Card>
                )}

                {/* STAGE: ROADMAP */}
                {activeStage === 'roadmap' && activeProject.roadmap && (
                  <Card className="border-border">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold tracking-tight text-foreground">
                        Timeline Execution Roadmap
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="space-y-4 max-h-[400px] overflow-y-auto pr-1">
                        {activeProject.roadmap.phases.map((phase: any) => (
                          <div key={phase.id} className="p-4 rounded-lg border border-border bg-muted/50 space-y-3">
                            <div className="flex justify-between items-center">
                              <span className="text-sm font-semibold text-foreground">{phase.name}</span>
                              <span className="badge-primary">Weeks {phase.startWeek} - {phase.endWeek}</span>
                            </div>
                            <div className="space-y-1.5 pl-3 border-l-2 border-primary/30 text-sm">
                              {phase.tasks.map((task: any) => (
                                <div key={task.id} className="text-muted-foreground">
                                  • {task.name} ({task.durationWeeks} weeks)
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Handoff CTA */}
                      <div className="pt-4 border-t border-border flex justify-end">
                        <Button 
                          onClick={() => setActiveStage('team-structure')}
                          className="gap-1.5"
                        >
                          <span>Define Team Hires</span>
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: ROADMAP EMPTY STATE */}
                {activeStage === 'roadmap' && !activeProject.roadmap && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                  <Card className="border-border p-12 flex flex-col items-center justify-center text-center space-y-6">
                    <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                      <LineChart className="h-8 w-8" />
                    </div>
                    <div className="space-y-2 max-w-md">
                      <h3 className="text-xl font-semibold text-foreground">Execution Roadmap Compiler</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        Translate your feature spec into a multi-phase, week-by-week development roadmap.
                      </p>
                    </div>
                    <Button 
                      onClick={() => handleStartGeneration(activeProject.id, 'roadmap')}
                      className="gap-2 px-6"
                    >
                      <Sparkles className="h-4 w-4" />
                      <span>Generate Timeline Roadmap</span>
                    </Button>
                  </Card>
                )}

                {/* STAGE: TEAM STRUCTURE */}
                {activeStage === 'team-structure' && activeProject.team && (
                  <Card className="border-border">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold tracking-tight text-foreground">
                        Resource Org Structure
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="space-y-3 max-h-[350px] overflow-y-auto pr-1">
                        {activeProject.team.roles.map((role: any) => (
                          <div key={role.id} className="p-4 rounded-lg border border-border bg-card flex items-center justify-between hover:bg-muted/50 transition-colors">
                            <div>
                              <span className="text-sm font-medium text-foreground block">{role.name}</span>
                              <span className="text-xs text-muted-foreground capitalize">{role.department.replace('_', ' ')} • Stage: {role.hiringStage}</span>
                            </div>
                            <span className="text-sm font-semibold text-primary">
                              {formatCost(role.monthlyCost)}/mo
                            </span>
                          </div>
                        ))}
                      </div>

                      {/* Handoff CTA */}
                      <div className="pt-4 border-t border-border flex justify-end">
                        <Button 
                          onClick={() => setActiveStage('swot')}
                          className="gap-1.5"
                        >
                          <span>Assess Strategic Risks</span>
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: TEAM STRUCTURE EMPTY STATE */}
                {activeStage === 'team-structure' && !activeProject.team && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                  <Card className="border-border p-12 flex flex-col items-center justify-center text-center space-y-6">
                    <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                      <Network className="h-8 w-8" />
                    </div>
                    <div className="space-y-2 max-w-md">
                      <h3 className="text-xl font-semibold text-foreground">Resource & Team Allocator</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        Forecast hiring requirements, define team roles, and calculate monthly salaries.
                      </p>
                    </div>
                    <Button 
                      onClick={() => handleStartGeneration(activeProject.id, 'team')}
                      className="gap-2 px-6"
                    >
                      <Sparkles className="h-4 w-4" />
                      <span>Plan Team Hires</span>
                    </Button>
                  </Card>
                )}

                {/* STAGE: SWOT ANALYSIS */}
                {activeStage === 'swot' && activeProject.swot && (
                  <Card className="border-border">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold tracking-tight text-foreground">
                        Strategic SWOT Board
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid grid-cols-2 gap-4">
                        {/* Strengths */}
                        <div className="p-4 rounded-lg border border-border bg-muted/50 space-y-2">
                          <span className="text-sm font-semibold text-foreground block">S - Strengths</span>
                          <div className="space-y-1.5 text-sm text-muted-foreground max-h-[120px] overflow-y-auto">
                            {activeProject.swot.items.filter((i: any) => i.type === 'strength').map((item: any) => (
                              <div key={item.id}>• {item.content}</div>
                            ))}
                          </div>
                        </div>
                        {/* Weaknesses */}
                        <div className="p-4 rounded-lg border border-border bg-muted/50 space-y-2">
                          <span className="text-sm font-semibold text-foreground block">W - Weaknesses</span>
                          <div className="space-y-1.5 text-sm text-muted-foreground max-h-[120px] overflow-y-auto">
                            {activeProject.swot.items.filter((i: any) => i.type === 'weakness').map((item: any) => (
                              <div key={item.id}>• {item.content}</div>
                            ))}
                          </div>
                        </div>
                        {/* Opportunities */}
                        <div className="p-4 rounded-lg border border-border bg-muted/50 space-y-2">
                          <span className="text-sm font-semibold text-foreground block">O - Opportunities</span>
                          <div className="space-y-1.5 text-sm text-muted-foreground max-h-[120px] overflow-y-auto">
                            {activeProject.swot.items.filter((i: any) => i.type === 'opportunity').map((item: any) => (
                              <div key={item.id}>• {item.content}</div>
                            ))}
                          </div>
                        </div>
                        {/* Threats */}
                        <div className="p-4 rounded-lg border border-border bg-muted/50 space-y-2">
                          <span className="text-sm font-semibold text-foreground block">T - Threats</span>
                          <div className="space-y-1.5 text-sm text-muted-foreground max-h-[120px] overflow-y-auto">
                            {activeProject.swot.items.filter((i: any) => i.type === 'threat').map((item: any) => (
                              <div key={item.id}>• {item.content}</div>
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* Handoff CTA */}
                      <div className="pt-4 border-t border-border flex justify-end">
                        <Button 
                          onClick={() => setActiveStage('cost-estimator')}
                          className="gap-1.5"
                        >
                          <span>Calculate Runway Costs</span>
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: SWOT EMPTY STATE */}
                {activeStage === 'swot' && !activeProject.swot && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                  <Card className="border-border p-12 flex flex-col items-center justify-center text-center space-y-6">
                    <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                      <TrendingUp className="h-8 w-8" />
                    </div>
                    <div className="space-y-2 max-w-md">
                      <h3 className="text-xl font-semibold text-foreground">Strategic SWOT Board</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        Compile strategic Strengths, Weaknesses, Opportunities, and Threats.
                      </p>
                    </div>
                    <Button 
                      onClick={() => handleStartGeneration(activeProject.id, 'swot')}
                      className="gap-2 px-6"
                    >
                      <Sparkles className="h-4 w-4" />
                      <span>Conduct SWOT Analysis</span>
                    </Button>
                  </Card>
                )}

                {/* STAGE: COST ESTIMATOR */}
                {activeStage === 'cost-estimator' && activeProject.cost && (
                  <Card className="border-border">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold tracking-tight text-foreground">
                        Startup Financial Projections
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid grid-cols-3 gap-4 text-center p-4 bg-muted rounded-lg">
                        <div>
                          <span className="text-xs text-muted-foreground block">MVP Cost</span>
                          <span className="text-lg font-bold text-foreground">{formatCost(activeProject.cost.mvpCost)}</span>
                        </div>
                        <div>
                          <span className="text-xs text-muted-foreground block">Year 1</span>
                          <span className="text-lg font-bold text-foreground">{formatCost(activeProject.cost.year1Cost)}</span>
                        </div>
                        <div>
                          <span className="text-xs text-muted-foreground block">Funding Required</span>
                          <span className="text-lg font-bold text-primary">{formatCost(activeProject.cost.fundingRequirement)}</span>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Planning estimates in USD, derived from team compensation, feature effort, and baseline operating allowances. Confirm quotes and local rates before committing.
                      </p>

                      <div className="space-y-3">
                        <span className="text-overline block">Estimated Monthly Operating Costs</span>
                        {activeProject.cost.costItems.length > 0 ? (
                          <div className="divide-y divide-border rounded-lg border border-border">
                            {activeProject.cost.costItems.map((item: any, idx: number) => (
                              <div key={`${item.name}-${idx}`} className="flex items-center justify-between gap-4 px-4 py-3">
                                <div className="min-w-0">
                                  <span className="block text-sm font-medium text-foreground">{item.name}</span>
                                  <span className="text-xs text-muted-foreground capitalize">{item.category} · estimated monthly</span>
                                </div>
                                <span className="shrink-0 text-sm font-semibold text-primary">
                                  {formatCost(item.amount)}/mo
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground">
                            Operating-cost estimates are unavailable. Regenerate the cost plan after confirming team and feature details.
                          </p>
                        )}
                      </div>

                      <div className="space-y-3">
                        <span className="text-overline block">Feature Development Estimates</span>
                        {activeProject.cost.featureCosts.length > 0 ? (
                          <div className="divide-y divide-border rounded-lg border border-border">
                            {activeProject.cost.featureCosts.map((feature: any, idx: number) => (
                              <div key={`${feature.featureId}-${idx}`} className="flex items-start justify-between gap-4 px-4 py-3">
                                <div className="min-w-0">
                                  <span className="block text-sm font-medium text-foreground">{feature.name}</span>
                                  <span className="text-xs text-muted-foreground">
                                    {feature.weeks} engineering weeks{feature.driver ? ` · ${feature.driver}` : ''}
                                  </span>
                                </div>
                                <span className="shrink-0 text-sm font-semibold text-primary">
                                  {formatCost(feature.amount)}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground">Feature effort details are not available yet.</p>
                        )}
                      </div>

                      <div className="space-y-3">
                        <span className="text-overline block">
                          Budget Scenarios
                        </span>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          {activeProject.cost.scenarios.map((scen: any) => (
                            <button
                              key={scen.id}
                              onClick={() => setSelectedScenario(scen.id)}
                              className={cn(
                                "p-4 rounded-lg border text-left transition-all space-y-2",
                                selectedScenario === scen.id 
                                  ? "border-primary bg-primary/5 shadow-sm" 
                                  : "border-border bg-card hover:bg-muted/50"
                              )}
                            >
                              <span className="text-xs font-semibold text-foreground block uppercase">{scen.name}</span>
                              <span className="text-lg font-bold text-primary block">{formatCost(scen.mvpCost)} MVP</span>
                              <span className="text-xs text-muted-foreground leading-relaxed block">{scen.description}</span>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Handoff CTA */}
                      <div className="pt-4 border-t border-border flex justify-end">
                        <Button 
                          onClick={() => setActiveStage('legal-compliance')}
                          className="gap-1.5"
                        >
                          <span>Continue to Legal &amp; Compliance</span>
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: COST ESTIMATOR EMPTY STATE */}
                {activeStage === 'cost-estimator' && !activeProject.cost && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                  <Card className="border-border p-12 flex flex-col items-center justify-center text-center space-y-6">
                    <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                      <Award className="h-8 w-8" />
                    </div>
                    <div className="space-y-2 max-w-md">
                      <h3 className="text-xl font-semibold text-foreground">Financial Plan & Cost Estimator</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        Model MVP costs, burn rates, runway forecasts, and funding requirements.
                      </p>
                    </div>
                    <Button 
                      onClick={() => handleStartGeneration(activeProject.id, 'cost')}
                      className="gap-2 px-6"
                    >
                      <Sparkles className="h-4 w-4" />
                      <span>Calculate Runway Costs</span>
                    </Button>
                  </Card>
                )}

                {/* STAGE: FINAL BLUEPRINT */}
                {activeStage === 'final-blueprint' && activeProject.blueprintCompiled && (
                  <Card className="border-border">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold tracking-tight text-foreground">
                        Compiled Startup Blueprint
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="p-8 rounded-xl border border-dashed border-border bg-muted flex flex-col items-center justify-center text-center space-y-4">
                        <div className="h-12 w-12 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400 font-bold text-lg">
                          ✓
                        </div>
                        <div className="space-y-1">
                          <span className="text-base font-semibold text-foreground block">Your Operating Blueprint is Complete</span>
                          <span className="text-sm text-muted-foreground">The compiled strategy plan has been generated and validated.</span>
                        </div>
                        <div className="flex gap-2">
                          <Button 
                            onClick={() => void handleDownloadBlueprintPdf(activeProject.id)}
                            disabled={isExportingPdf}
                            className="gap-1.5"
                          >
                            {isExportingPdf && <Loader2 className="h-4 w-4 animate-spin" />}
                            {isExportingPdf ? 'Preparing PDF Package…' : 'Download PDF Package'}
                          </Button>
                          <Button 
                            onClick={async () => {
                              try {
                                const payload = await api.exports.share(activeProject.id);
                                const url = `${window.location.origin}/shared/${payload.token}`;
                                setStreamLog(prev => [`Generated shareable link: ${url}`, ...prev]);
                                alert(`Investor link created: ${url}`);
                              } catch (err: any) {
                                alert(`Failed to share: ${err.message}`);
                              }
                            }}
                            variant="outline" 
                            className="h-8 text-xs"
                          >
                            Share Secure Web View
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: FINAL BLUEPRINT EMPTY STATE */}
                {activeStage === 'final-blueprint' && !activeProject.blueprintCompiled && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                  <Card className="shadow-lvl-2 border-border/60 bg-white/70 backdrop-blur-xl p-8 flex flex-col items-center justify-center text-center space-y-6">
                    <div className="h-14 w-14 rounded-full bg-accent-blue/10 flex items-center justify-center text-accent-blue">
                      <ScrollText className="h-7 w-7" />
                    </div>
                    <div className="space-y-2 max-w-md">
                      <h3 className="text-lg font-bold text-primary">Startup Blueprint Compiler</h3>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        Assemble all generated modules into an investor-ready, comprehensive operating blueprint packet with secure sharing and PDF export options.
                      </p>
                    </div>
                    <Button 
                      onClick={() => handleStartGeneration(activeProject.id, 'blueprint')}
                      className="h-9 text-xs gap-1.5 px-6 font-medium shadow-sm"
                    >
                      <Sparkles className="h-4 w-4" />
                      <span>Compile Final Blueprint</span>
                    </Button>
                  </Card>
                )}

                {/* ═══════════════════════════════════════════════════════════════════
                    INTELLIGENCE STAGES (7-14)
                    ═══════════════════════════════════════════════════════════════════ */}

                {/* STAGE: LEGAL & COMPLIANCE */}
                {activeStage === 'legal-compliance' && activeProject.legalCompliance && (
                  <Card className="border-border">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Legal & Compliance Review
                      </CardTitle>
                      <div className={cn(
                        "text-xs px-2.5 py-1 rounded font-medium flex items-center gap-1.5",
                        activeProject.legalCompliance.overall_risk === 'low' ? 'bg-green-50 text-green-700' :
                        activeProject.legalCompliance.overall_risk === 'medium' ? 'bg-yellow-50 text-yellow-700' :
                        'bg-red-50 text-red-700'
                      )}>
                        <Shield className="h-4 w-4" />
                        <span>Risk: {activeProject.legalCompliance.overall_risk}</span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {activeProject.legalCompliance.summary && (
                        <p className="rounded-lg border border-border bg-muted/40 p-4 text-sm leading-relaxed text-muted-foreground">
                          {activeProject.legalCompliance.summary}
                        </p>
                      )}
                      <div className="flex items-center justify-between rounded-lg border border-border px-4 py-3">
                        <span className="text-sm font-medium text-foreground">Initial compliance budget estimate</span>
                        <span className="text-sm font-semibold text-primary">
                          {activeProject.legalCompliance.estimated_compliance_budget_usd
                            ? formatCost(activeProject.legalCompliance.estimated_compliance_budget_usd)
                            : 'Not verified'}
                        </span>
                      </div>
                      {/* Compliance Checklist */}
                      <div className="space-y-3">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                          Compliance Checklist
                        </span>
                        <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                          {(activeProject.legalCompliance.compliance_checklist || []).map((item: any, idx: number) => (
                            <div key={idx} className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-white">
                              <div className={cn(
                                "h-5 w-5 rounded-full flex items-center justify-center shrink-0 mt-0.5",
                                item.status === 'compliant' ? 'bg-green-100 text-green-600' :
                                item.status === 'pending' ? 'bg-yellow-100 text-yellow-600' :
                                item.status === 'gap' ? 'bg-red-100 text-red-600' :
                                'bg-gray-100 text-gray-400'
                              )}>
                                {item.status === 'compliant' ? '✓' : item.status === 'gap' ? '!' : '○'}
                              </div>
                              <div className="flex-1 min-w-0">
                                <span className="text-sm font-medium text-primary block">{item.item}</span>
                                {item.notes && <span className="text-xs text-muted-foreground">{item.notes}</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* IP Protection & Registrations */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            IP Protection
                          </span>
                          {(activeProject.legalCompliance.ip_protection || []).map((ip: any, idx: number) => (
                            <div key={idx} className="p-2 rounded bg-muted text-xs">
                              <span className="font-medium text-primary">{ip.asset}</span>
                              <span className="text-muted-foreground block">{ip.protection_type}</span>
                            </div>
                          ))}
                        </div>
                        <div className="space-y-2">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            Registrations Needed
                          </span>
                          {(activeProject.legalCompliance.registrations_needed || []).map((reg: any, idx: number) => (
                            <div key={idx} className="p-2 rounded bg-muted text-xs">
                              <span className="font-medium text-primary">{reg.type}</span>
                              <span className="text-muted-foreground block">{reg.jurisdiction} • {reg.timeline}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {(activeProject.legalCompliance.regulatory_requirements || []).length > 0 && (
                        <div className="space-y-2">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            Regulatory Authorities & Directories
                          </span>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {activeProject.legalCompliance.regulatory_requirements.map((entry: any, idx: number) => (
                              <div key={idx} className="rounded-lg border border-border bg-muted/40 p-3 text-xs">
                                <span className="block font-semibold text-primary">{entry.regulation}</span>
                                <span className="mt-1 block text-muted-foreground">{entry.applicability}</span>
                                <span className="mt-1 block text-muted-foreground">{entry.action_needed}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {(activeProject.legalCompliance.data_protection_requirements || []).length > 0 && (
                        <div className="space-y-2">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            Data Protection & Privacy
                          </span>
                          <div className="space-y-1.5 rounded-lg border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
                            {activeProject.legalCompliance.data_protection_requirements.map((requirement: string, idx: number) => (
                              <p key={idx}>• {requirement}</p>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Grants & Incentives */}
                      {(activeProject.legalCompliance.grants_incentives || []).length > 0 && (
                        <div className="space-y-2">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            Available Grants & Incentives
                          </span>
                          <div className="grid grid-cols-2 gap-2">
                            {(activeProject.legalCompliance.grants_incentives || []).map((grant: any, idx: number) => (
                              <div key={idx} className="p-3 rounded-lg border border-green-200 bg-green-50/50 text-xs">
                                <span className="font-semibold text-primary block">{grant.name}</span>
                                <span className="text-muted-foreground">{grant.eligibility} • {grant.value}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Recommendations */}
                      {activeProject.legalCompliance.recommendations.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            Recommendations
                          </span>
                          <div className="space-y-1.5 text-xs text-muted-foreground">
                            {activeProject.legalCompliance.recommendations.map((rec: string, idx: number) => (
                              <div key={idx}>• {rec}</div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: COMPETITIVE MOAT */}
                {activeStage === 'competitive-moat' && activeProject.competitiveMoat && (
                  <Card className="border-border">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Competitive Moat Analysis
                      </CardTitle>
                      <div className="text-xs px-2.5 py-1 rounded bg-accent-blue/10 text-accent-blue font-medium flex items-center gap-1.5">
                        <Target className="h-4 w-4" />
                        <span>Moat Strength: {activeProject.competitiveMoat.overall_moat_strength}/100</span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Competitor Landscape */}
                      <div className="space-y-3">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                          Competitor Landscape
                        </span>
                        <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                          {(activeProject.competitiveMoat.competitors || []).map((comp: any, idx: number) => (
                            <div key={idx} className="p-3 rounded-lg border border-border/60 bg-white flex items-center justify-between">
                              <div className="flex-1 min-w-0">
                                <span className="text-sm font-semibold text-primary block">{comp.name}</span>
                                <span className="text-xs text-muted-foreground block truncate">{comp.strength}</span>
                              </div>
                              <span className={cn(
                                "text-[10px] font-semibold uppercase px-2 py-0.5 rounded shrink-0",
                                comp.threat_level === 'high' ? 'bg-red-100 text-red-700' :
                                comp.threat_level === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                'bg-green-100 text-green-700'
                              )}>
                                {comp.threat_level}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Moat Scores */}
                      <div className="space-y-3">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                          Moat Dimensions
                        </span>
                        <div className="grid grid-cols-2 gap-3">
                          {(activeProject.competitiveMoat.moat_scores || []).map((score: any, idx: number) => (
                            <div key={idx} className="p-3 rounded-lg border border-border/60 bg-muted/50">
                              <div className="flex justify-between items-center mb-2">
                                <span className="text-xs font-medium text-primary">{score.dimension}</span>
                                <span className="text-xs font-bold text-accent-blue">{score.score}/100</span>
                              </div>
                              <div className="h-1.5 bg-black/5 rounded-full overflow-hidden">
                                <div 
                                  className="h-full bg-accent-blue rounded-full transition-all"
                                  style={{ width: `${score.score}%` }}
                                />
                              </div>
                              {score.evidence && (
                                <span className="text-[10px] text-muted-foreground mt-1 block truncate">{score.evidence}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Recommendations */}
                      {activeProject.competitiveMoat.strategic_recommendations.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            Strategic Recommendations
                          </span>
                          <div className="space-y-1.5 text-xs text-muted-foreground">
                            {activeProject.competitiveMoat.strategic_recommendations.map((rec: string, idx: number) => (
                              <div key={idx}>• {rec}</div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: STRESS TEST */}
                {activeStage === 'stress-test' && activeProject.stressTest && (
                  <Card className="border-border">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Market Stress Test
                      </CardTitle>
                      <div className="text-xs px-2.5 py-1 rounded bg-accent-blue/10 text-accent-blue font-medium flex items-center gap-1.5">
                        <Zap className="h-4 w-4" />
                        <span>Resilience: {activeProject.stressTest.resilience_score}/100</span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Scenario Cards */}
                      <div className="space-y-3">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                          Stress Scenarios
                        </span>
                        <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                          {(activeProject.stressTest.scenarios || []).map((scenario: any, idx: number) => (
                            <div key={idx} className="p-4 rounded-lg border border-border/60 bg-muted/50 space-y-2">
                              <div className="flex justify-between items-center">
                                <span className="text-sm font-semibold text-primary">{scenario.name}</span>
                                <div className="flex gap-2">
                                  <span className={cn(
                                    "text-[10px] font-semibold uppercase px-2 py-0.5 rounded",
                                    scenario.probability === 'high' ? 'bg-red-100 text-red-700' :
                                    scenario.probability === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                    'bg-green-100 text-green-700'
                                  )}>
                                    {scenario.probability} prob
                                  </span>
                                  <span className={cn(
                                    "text-[10px] font-semibold uppercase px-2 py-0.5 rounded",
                                    scenario.impact === 'high' ? 'bg-red-100 text-red-700' :
                                    scenario.impact === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                    'bg-green-100 text-green-700'
                                  )}>
                                    {scenario.impact} impact
                                  </span>
                                </div>
                              </div>
                              <p className="text-xs text-muted-foreground">{scenario.description}</p>
                              <div className="text-xs">
                                <span className="text-muted-foreground">Mitigation: </span>
                                <span className="text-primary">{scenario.mitigation}</span>
                              </div>
                              {scenario.recovery_time && (
                                <div className="text-xs">
                                  <span className="text-muted-foreground">Recovery: </span>
                                  <span className="text-primary">{scenario.recovery_time}</span>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Critical Dependencies */}
                      {activeProject.stressTest.critical_dependencies.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            Critical Dependencies
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {activeProject.stressTest.critical_dependencies.map((dep: string, idx: number) => (
                              <span key={idx} className="text-xs px-2 py-1 rounded bg-red-50 text-red-700 border border-red-200">
                                {dep}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: FINANCIAL INTELLIGENCE */}
                {activeStage === 'financial-intelligence' && activeProject.financialIntelligence && (
                  <Card className="border-border">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Financial Intelligence
                      </CardTitle>
                      <div className="text-xs px-2.5 py-1 rounded bg-accent-blue/10 text-accent-blue font-medium flex items-center gap-1.5">
                        <BarChart3 className="h-4 w-4" />
                        <span>Health: {activeProject.financialIntelligence.financial_health_score}/100</span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Unit Economics */}
                      <div className="space-y-3">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                          Unit Economics
                        </span>
                        {(activeProject.financialIntelligence.unit_economics_assumptions?.length ?? 0) > 0 && (
                          <div className="rounded-lg border border-amber-200 bg-amber-50/70 px-3 py-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
                            Illustrative planning estimates, not verified company results. Validate pricing, retention, and acquisition costs before using these figures.
                            <ul className="mt-1 list-disc pl-4">
                              {activeProject.financialIntelligence.unit_economics_assumptions?.map((assumption, idx) => (
                                <li key={idx}>{assumption}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                          {(activeProject.financialIntelligence.unit_economics || []).map((item: any, idx: number) => (
                            <div key={idx} className="p-3 rounded-lg border border-border/60 bg-muted/50 text-center">
                              <span className="text-[10px] text-muted-foreground block">{item.metric}</span>
                              <span className="text-lg font-bold text-primary">
                                {item.benchmark === 'USD'
                                  ? `$${Number(item.value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`
                                  : item.benchmark === '%'
                                    ? `${item.value}%`
                                    : item.benchmark === 'ratio'
                                      ? `${item.value}x`
                                      : item.benchmark === 'months'
                                        ? `${item.value} mo`
                                        : item.value}
                              </span>
                              {item.benchmark && (
                                <span className="text-[10px] text-muted-foreground block">Unit: {item.benchmark}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Projections Table */}
                      <div className="space-y-3">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                          Financial Projections
                        </span>
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="border-b border-border">
                                {activeProject.financialIntelligence?.projection_format === 'period' ? (
                                  <>
                                    <th className="text-left py-2 font-semibold text-muted-foreground">Period</th>
                                    <th className="text-right py-2 font-semibold text-muted-foreground">Revenue</th>
                                    <th className="text-right py-2 font-semibold text-muted-foreground">Costs</th>
                                    <th className="text-right py-2 font-semibold text-muted-foreground">Profit</th>
                                    <th className="text-right py-2 font-semibold text-muted-foreground">Cash Balance</th>
                                  </>
                                ) : (
                                  <>
                                    <th className="text-left py-2 font-semibold text-muted-foreground">Metric</th>
                                    <th className="text-right py-2 font-semibold text-muted-foreground">Month 1</th>
                                    <th className="text-right py-2 font-semibold text-muted-foreground">Month 6</th>
                                    <th className="text-right py-2 font-semibold text-muted-foreground">Month 12</th>
                                    <th className="text-right py-2 font-semibold text-muted-foreground">Month 24</th>
                                  </>
                                )}
                              </tr>
                            </thead>
                            <tbody>
                              {(activeProject.financialIntelligence?.projections || []).map((proj: any, idx: number) => (
                                <tr key={idx} className="border-b border-border/50">
                                  {activeProject.financialIntelligence?.projection_format === 'period' ? (
                                    <>
                                      <td className="py-2 text-primary font-medium">{proj.period}</td>
                                      <td className="py-2 text-right text-muted-foreground">{proj.revenue}</td>
                                      <td className="py-2 text-right text-muted-foreground">{proj.costs}</td>
                                      <td className="py-2 text-right text-muted-foreground">{proj.profit}</td>
                                      <td className="py-2 text-right text-muted-foreground">{proj.cash_balance}</td>
                                    </>
                                  ) : (
                                    <>
                                      <td className="py-2 text-primary font-medium">{proj.metric}</td>
                                      <td className="py-2 text-right text-muted-foreground">{proj.month_1}</td>
                                      <td className="py-2 text-right text-muted-foreground">{proj.month_6}</td>
                                      <td className="py-2 text-right text-muted-foreground">{proj.month_12}</td>
                                      <td className="py-2 text-right text-muted-foreground">{proj.month_24}</td>
                                    </>
                                  )}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: INVESTMENT COMMITTEE */}
                {activeStage === 'investment-committee' && activeProject.investmentCommittee && (
                  <Card className="border-border">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Investment Committee
                      </CardTitle>
                      <div className={cn(
                        "text-xs px-2.5 py-1 rounded font-medium flex items-center gap-1.5",
                        activeProject.investmentCommittee.overall_score >= 70 ? 'bg-green-50 text-green-700' :
                        activeProject.investmentCommittee.overall_score >= 50 ? 'bg-yellow-50 text-yellow-700' :
                        'bg-red-50 text-red-700'
                      )}>
                        <Users className="h-4 w-4" />
                        <span>Score: {activeProject.investmentCommittee.overall_score}/100</span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Partner Cards */}
                      <div className="space-y-3">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                          Partner Votes
                        </span>
                        <div className="space-y-3">
                          {(activeProject.investmentCommittee.partner_cards || []).map((partner: any, idx: number) => (
                            <div key={idx} className="p-4 rounded-lg border border-border/60 bg-muted/50 space-y-2">
                              <div className="flex justify-between items-center">
                                <div>
                                  <span className="text-sm font-semibold text-primary">{partner.name}</span>
                                  <span className="text-xs text-muted-foreground ml-2">{partner.role}</span>
                                </div>
                                <span className={cn(
                                  "text-[10px] font-bold uppercase px-2 py-1 rounded",
                                  partner.vote === 'approve' ? 'bg-green-100 text-green-700' :
                                  partner.vote === 'conditional' ? 'bg-yellow-100 text-yellow-700' :
                                  partner.vote === 'reject' ? 'bg-red-100 text-red-700' :
                                  'bg-gray-100 text-gray-600'
                                )}>
                                  {partner.vote}
                                </span>
                              </div>
                              <p className="text-xs text-muted-foreground">{partner.reasoning}</p>
                              {partner.concerns?.length > 0 && (
                                <div className="space-y-1">
                                  {partner.concerns.map((concern: string, cIdx: number) => (
                                    <span key={cIdx} className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-50 text-yellow-700 block">
                                      ⚠ {concern}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Recommendation */}
                      <div className="p-4 rounded-lg border border-accent-blue/20 bg-accent-blue/5">
                        <span className="text-xs font-semibold text-accent-blue block mb-2">Investment Recommendation</span>
                        <p className="text-sm text-primary">
                          {formatInvestmentRecommendation(activeProject.investmentCommittee.investment_recommendation)}
                        </p>
                      </div>

                      {/* Due Diligence */}
                      {(activeProject.investmentCommittee.due_diligence || []).length > 0 && (
                        <div className="space-y-2">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            Due Diligence
                          </span>
                          <div className="space-y-1.5">
                            {activeProject.investmentCommittee.due_diligence.map((dd: any, idx: number) => (
                              <div key={idx} className="flex items-center gap-2 text-xs">
                                <span className={cn(
                                  "h-2 w-2 rounded-full shrink-0",
                                  dd.status === 'pass' ? 'bg-green-500' :
                                  dd.status === 'flag' ? 'bg-yellow-500' : 'bg-red-500'
                                )} />
                                <span className="text-primary font-medium">{dd.area}</span>
                                <span className="text-muted-foreground">— {dd.notes}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: PRODUCT EXECUTION */}
                {activeStage === 'product-execution' && activeProject.productExecution && (
                  <Card className="border-border">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Product Execution Plan
                      </CardTitle>
                      <div className="text-xs px-2.5 py-1 rounded bg-accent-blue/10 text-accent-blue font-medium flex items-center gap-1.5">
                        <Rocket className="h-4 w-4" />
                        <span>Plan Confidence: {activeProject.productExecution.plan_confidence}%</span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {activeProject.productExecution.product_vision && (
                        <div className="rounded-lg border border-accent-blue/20 bg-accent-blue/5 p-4">
                          <span className="mb-2 block text-xs font-semibold text-accent-blue">Product Vision</span>
                          <p className="text-sm leading-relaxed text-primary">{activeProject.productExecution.product_vision}</p>
                        </div>
                      )}

                      {/* PRD Summary */}
                      <div className="p-4 rounded-lg bg-muted">
                        <span className="text-xs font-semibold text-muted-foreground block mb-2">PRD Summary</span>
                        <p className="text-sm text-primary leading-relaxed">{activeProject.productExecution.prd_summary}</p>
                      </div>

                      {/* Sprint Plan */}
                      <div className="space-y-3">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                          Sprint Plan
                        </span>
                        <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                          {(activeProject.productExecution.sprint_plan || []).map((sprint: any, idx: number) => (
                            <div key={idx} className="p-3 rounded-lg border border-border/60 bg-white flex items-center justify-between">
                              <div className="flex-1 min-w-0">
                                <span className="text-sm font-semibold text-primary block">
                                  Sprint {sprint.sprint}: {sprint.name}
                                </span>
                                <span className="text-xs text-muted-foreground">{sprint.duration_weeks} weeks</span>
                                {sprint.total_effort_points > 0 && (
                                  <span className="text-xs text-muted-foreground"> · {sprint.total_effort_points} effort points</span>
                                )}
                              </div>
                              <div className="flex flex-wrap gap-1 justify-end max-w-[200px]">
                                {(sprint.goals || []).slice(0, 2).map((goal: string, gIdx: number) => (
                                  <span key={gIdx} className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700">
                                    {goal}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {activeProject.productExecution.user_stories.length > 0 && (
                        <div className="space-y-3">
                          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                            User Stories ({activeProject.productExecution.user_stories.length})
                          </span>
                          <div className="max-h-[320px] space-y-2 overflow-y-auto pr-1">
                            {activeProject.productExecution.user_stories.map((story: any) => (
                              <div key={story.id} className="rounded-lg border border-border/60 bg-white p-3">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <span className="text-sm font-semibold text-primary">{story.id}: {story.title}</span>
                                  <span className="rounded bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                                    {story.priority} · {story.effort_estimate}
                                  </span>
                                </div>
                                <p className="mt-1 text-xs text-muted-foreground">
                                  As {story.user_type}, I want to {story.action} so that {story.benefit}.
                                </p>
                                {(story.acceptance_criteria || []).length > 0 && (
                                  <ul className="mt-2 space-y-1 pl-4 text-xs text-muted-foreground">
                                    {story.acceptance_criteria.map((criterion: string, idx: number) => (
                                      <li key={idx} className="list-disc">{criterion}</li>
                                    ))}
                                  </ul>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Architecture */}
                      {(activeProject.productExecution.architecture || []).length > 0 && (
                        <div className="space-y-3">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            Architecture
                          </span>
                          <div className="space-y-2">
                            {activeProject.productExecution.architecture.map((arch: any, idx: number) => (
                              <div key={idx} className="p-3 rounded-lg border border-border/60 bg-muted/50 flex items-center justify-between">
                                <div>
                                  <span className="text-sm font-medium text-primary block">{arch.component}</span>
                                  <span className="text-xs text-muted-foreground">{arch.rationale}</span>
                                </div>
                                {arch.technology && (
                                  <span className="text-xs font-semibold text-accent-blue">{arch.technology}</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {(activeProject.productExecution.architecture_overview
                        || activeProject.productExecution.data_flow
                        || activeProject.productExecution.infrastructure
                        || activeProject.productExecution.security_considerations.length > 0) && (
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                          {[
                            ['Architecture Overview', activeProject.productExecution.architecture_overview],
                            ['Data Flow', activeProject.productExecution.data_flow],
                            ['Infrastructure', activeProject.productExecution.infrastructure],
                          ].filter(([, value]) => value).map(([label, value]) => (
                            <div key={label as string} className="rounded-lg border border-border bg-muted/40 p-3">
                              <span className="mb-1 block text-xs font-semibold text-primary">{label}</span>
                              <p className="text-xs leading-relaxed text-muted-foreground">{value}</p>
                            </div>
                          ))}
                          {activeProject.productExecution.security_considerations.length > 0 && (
                            <div className="rounded-lg border border-border bg-muted/40 p-3">
                              <span className="mb-1 block text-xs font-semibold text-primary">Security Considerations</span>
                              <ul className="space-y-1 text-xs text-muted-foreground">
                                {activeProject.productExecution.security_considerations.map((item: string, idx: number) => (
                                  <li key={idx}>• {item}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}

                      {activeProject.productExecution.api_endpoints.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Key API Endpoints</span>
                          <div className="divide-y divide-border rounded-lg border border-border">
                            {activeProject.productExecution.api_endpoints.map((endpoint: any, idx: number) => (
                              <div key={`${endpoint.method}-${endpoint.path}-${idx}`} className="flex flex-wrap items-center gap-2 px-3 py-2 text-xs">
                                <span className="rounded bg-blue-50 px-2 py-0.5 font-semibold text-blue-700">{endpoint.method}</span>
                                <code className="text-primary">{endpoint.path}</code>
                                <span className="text-muted-foreground">{endpoint.description}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {activeProject.productExecution.release_plan.features.length > 0 && (
                        <div className="space-y-3 rounded-lg border border-border p-4">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-sm font-semibold text-primary">
                              {activeProject.productExecution.release_plan.release_name} ({activeProject.productExecution.release_plan.version})
                            </span>
                            <span className="text-xs text-muted-foreground">Target: {activeProject.productExecution.release_plan.target_date}</span>
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {activeProject.productExecution.release_plan.features.map((feature: string, idx: number) => (
                              <span key={idx} className="rounded bg-muted px-2 py-1 text-xs text-foreground">{feature}</span>
                            ))}
                          </div>
                          {activeProject.productExecution.release_plan.milestones.map((milestone: any, idx: number) => (
                            <p key={idx} className="text-xs text-muted-foreground">
                              <strong className="text-primary">{milestone.name}:</strong> {milestone.target}
                            </p>
                          ))}
                          {activeProject.productExecution.release_plan.success_metrics.length > 0 && (
                            <div>
                              <strong className="text-xs text-primary">Success Metrics</strong>
                              <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                                {activeProject.productExecution.release_plan.success_metrics.map((metric: string, idx: number) => (
                                  <li key={idx}>• {metric}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          <p className="text-xs text-muted-foreground">
                            <strong className="text-primary">Rollback:</strong> {activeProject.productExecution.release_plan.rollback_plan}
                          </p>
                        </div>
                      )}

                      {(activeProject.productExecution.qa_strategy.length > 0
                        || activeProject.productExecution.deployment_strategy.length > 0) && (
                        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                          {[
                            ['QA Strategy', activeProject.productExecution.qa_strategy],
                            ['Deployment Strategy', activeProject.productExecution.deployment_strategy],
                          ].map(([heading, items]) => (
                            <div key={heading as string} className="rounded-lg border border-border bg-muted/40 p-3">
                              <span className="mb-2 block text-xs font-semibold text-primary">{heading}</span>
                              <ul className="space-y-1 text-xs text-muted-foreground">
                                {(items as string[]).map((item, idx) => <li key={idx}>• {item}</li>)}
                              </ul>
                            </div>
                          ))}
                        </div>
                      )}

                      {activeProject.productExecution.explanation && (
                        <p className="text-xs leading-relaxed text-muted-foreground">
                          {activeProject.productExecution.explanation}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: GLOBAL EXPANSION */}
                {activeStage === 'global-expansion' && activeProject.globalExpansion && (
                  <Card className="border-border">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Global Expansion Strategy
                      </CardTitle>
                      <div className="text-xs px-2.5 py-1 rounded bg-accent-blue/10 text-accent-blue font-medium flex items-center gap-1.5">
                        <Globe className="h-4 w-4" />
                        <span>TAM: {activeProject.globalExpansion.total_addressable_market_global || 'N/A'}</span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Target Markets */}
                      <div className="space-y-3">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                          Target Markets
                        </span>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                          {(activeProject.globalExpansion.target_markets || []).map((market: any, idx: number) => (
                            <div key={idx} className="p-3 rounded-lg border border-border/60 bg-muted/50">
                              <div className="flex justify-between items-center mb-2">
                                <span className="text-sm font-semibold text-primary">{market.country}</span>
                                <span className={cn(
                                  "text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded",
                                  market.priority === 'high' ? 'bg-green-100 text-green-700' :
                                  market.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-gray-100 text-gray-600'
                                )}>
                                  {market.priority}
                                </span>
                              </div>
                              <div className="space-y-1 text-xs">
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Market Size</span>
                                  <span className="text-primary font-medium">{market.market_size}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Growth</span>
                                  <span className="text-primary font-medium">{market.growth_rate}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Entry</span>
                                  <span className="text-primary font-medium capitalize">{market.entry_difficulty}</span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Expansion Waves */}
                      {(activeProject.globalExpansion.expansion_waves || []).length > 0 && (
                        <div className="space-y-3">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            Expansion Waves
                          </span>
                          <div className="space-y-3">
                            {activeProject.globalExpansion.expansion_waves.map((wave: any, idx: number) => (
                              <div key={idx} className="p-3 rounded-lg border border-border/60 bg-white">
                                <div className="flex justify-between items-center mb-2">
                                  <span className="text-sm font-semibold text-primary">Wave {wave.wave}</span>
                                  <span className="text-xs text-muted-foreground">{wave.timeline}</span>
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                  {(wave.markets || []).map((m: string, mIdx: number) => (
                                    <span key={mIdx} className="text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-700">
                                      {m}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Recommendations */}
                      {activeProject.globalExpansion.recommendations.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            Recommendations
                          </span>
                          <div className="space-y-1.5 text-xs text-muted-foreground">
                            {activeProject.globalExpansion.recommendations.map((rec: string, idx: number) => (
                              <div key={idx}>• {rec}</div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* ═══════════════════════════════════════════════════════════════════
                    EMPTY STATES FOR INTELLIGENCE STAGES
                    ═══════════════════════════════════════════════════════════════════ */}

                {['legal-compliance', 'competitive-moat', 'stress-test', 'financial-intelligence', 'investment-committee', 'product-execution', 'global-expansion'].map((stage) => {
                  const stageKey = stage.replace('-', '') as keyof typeof isStageCompleted;
                  const hasData = isStageCompleted(stage as StageName, activeProject);
                  const Icon = STAGE_ICONS[stage as StageName] || Shield;
                  const labels: Record<string, { title: string; desc: string; btn: string }> = {
                    'legal-compliance': { title: 'Legal & Compliance Review', desc: 'Analyze regulatory requirements, IP protection strategy, compliance checklist, and available grants or incentives.', btn: 'Run Legal Analysis' },
                    'competitive-moat': { title: 'Competitive Moat Analysis', desc: 'Map competitor landscape, score moat dimensions, assess copy difficulty, and identify strategic positioning.', btn: 'Analyze Competitive Moat' },
                    'stress-test': { title: 'Market Stress Test', desc: 'Simulate adverse market scenarios, evaluate resilience, identify critical dependencies, and plan mitigations.', btn: 'Run Stress Test' },
                    'financial-intelligence': { title: 'Financial Intelligence', desc: 'Project revenue metrics, unit economics, funding requirements, and valuation scenarios.', btn: 'Generate Financial Intelligence' },
                    'investment-committee': { title: 'Investment Committee', desc: 'Simulate partner votes, evaluate investment readiness, due diligence, and term sheet recommendations.', btn: 'Run Investment Committee' },
                    'product-execution': { title: 'Product Execution Plan', desc: 'Define PRD, sprint plan, architecture decisions, API endpoints, and launch readiness.', btn: 'Create Execution Plan' },
                    'global-expansion': { title: 'Global Expansion Strategy', desc: 'Identify target markets, plan expansion waves, localize strategy, and assess global risks.', btn: 'Plan Global Expansion' },
                  };
                  const info = labels[stage] || { title: stage, desc: '', btn: 'Run' };

                  if (activeStage === stage && !hasData && activeProject.status !== 'generating' && activeProject.status !== 'error') {
                    return (
                      <Card key={stage} className="shadow-lvl-2 border-border/60 bg-white/70 backdrop-blur-xl p-8 flex flex-col items-center justify-center text-center space-y-6">
                        <div className="h-14 w-14 rounded-full bg-accent-blue/10 flex items-center justify-center text-accent-blue">
                          <Icon className="h-7 w-7" />
                        </div>
                        <div className="space-y-2 max-w-md">
                          <h3 className="text-lg font-bold text-primary">{info.title}</h3>
                          <p className="text-xs text-muted-foreground leading-relaxed">{info.desc}</p>
                        </div>
                        <Button 
                          onClick={() => handleStartGeneration(activeProject.id, getBackendStageName(stage))}
                          className="h-9 text-xs gap-1.5 px-6 font-medium shadow-sm"
                        >
                          <Sparkles className="h-4 w-4" />
                          <span>{info.btn}</span>
                        </Button>
                      </Card>
                    );
                  }
                  return null;
                })}
              </div>

              {/* AI Reasoning Feed - Collapsible sidebar */}
              <div className="mt-6">
                <GlassPanel shadow="sm" className="p-4 bg-card">
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="h-4 w-4 text-primary" />
                    <span className="text-sm font-semibold text-foreground">Activity Log</span>
                  </div>

                  <div className="max-h-[200px] overflow-y-auto space-y-1.5 text-xs text-muted-foreground">
                    {streamLog.map((log, i) => (
                      <div key={i} className="flex items-start gap-2 py-1">
                        <div className="h-1.5 w-1.5 rounded-full bg-primary shrink-0 mt-1.5" />
                        <span>{log}</span>
                      </div>
                    ))}
                    {streamLog.length === 0 && (
                      <span className="text-muted-foreground/50 italic text-center block py-4">
                        Activity will appear here during generation.
                      </span>
                    )}
                  </div>
                </GlassPanel>
              </div>
            </WorkspaceView>
          )}
        </main>
      </div>
    </div>
  );
}
