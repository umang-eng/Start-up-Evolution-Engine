'use client';

import React, { useState, useEffect, useTransition, useCallback } from 'react';
import { useBlueprintStore } from '@/store/use-blueprint-store';
import { useAuth } from '@/components/shared/auth-provider';
import { usePipelineStore } from '@/store/use-pipeline-store';
import { useNotificationStore } from '@/store/use-notification-store';
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

const STAGE_ORDER: StageName[] = [
  'dna-analyzer',
  'feature-extractor',
  'roadmap',
  'team-structure',
  'swot',
  'cost-estimator',
  'final-blueprint',
  'legal-compliance',
  'competitive-moat',
  'stress-test',
  'financial-intelligence',
  'investment-committee',
  'product-execution',
  'global-expansion',
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

export default function WorkspacePage() {
  const { 
    projects, 
    activeProjectId, 
    activeStage,
    setActiveStage,
    loadProjects,
    createNewProject,
    updateProjectStatus,
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
    saveGlobalExpansion
  } = useBlueprintStore();

  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [inputVal, setInputVal] = useState('');
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<'model' | 'target' | 'usp'>('model');
  const [selectedScenario, setSelectedScenario] = useState<'lean' | 'balanced' | 'aggressive'>('lean');
  const [isPending, startTransition] = useTransition();

  const activeProject = projects.find(p => p.id === activeProjectId);
  const { currencySymbol, costBuffer } = useSettingsStore();

  const formatCost = (amount: number) => {
    const paddedAmount = amount * (1 + (costBuffer || 0) / 100);
    return `${currencySymbol || '$'}${Math.round(paddedAmount).toLocaleString()}`;
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

  // AI-powered idea enhancement — calls real Gemini backend
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
  const handleStartGeneration = async (projId: string, stage: string) => {
    updateProjectStatus(projId, 'generating');
    setStreamLog([`Contacting intelligence orchestrator for stage [${stage.toUpperCase()}]...`]);

    const token = getAccessToken();
    if (!token) {
      setStreamLog(prev => ["❌ Error: Authentication credentials missing. Please log in again.", ...prev]);
      updateProjectStatus(projId, 'error');
      return;
    }

    try {
      // 1. Trigger Async execution run
      await api.generator.run(projId, stage);
      setStreamLog(prev => ["✅ Generation pipeline triggered. Opening stream connection...", ...prev]);

      // 2. Open EventSource connection with token query param
      const eventSourceUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/streams/progress/${projId}?token=${encodeURIComponent(token)}`;
      const es = new EventSource(eventSourceUrl);
      let consecutiveErrors = 0;
      const MAX_ERRORS = 5;

      es.addEventListener('system:init', () => {
        setStreamLog(prev => ["🔗 Stream channel established.", ...prev]);
      });

      es.addEventListener('workflow:started', () => {
        setStreamLog(prev => ["🚀 Pipeline running — evolving startup DNA architecture...", ...prev]);
      });

      es.addEventListener('module:started', (e: any) => {
        try {
          const data = JSON.parse(e.data);
          const stageName = data.module_info?.module_name || '';
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

          setStreamLog(prev => [`✅ Stage [${stageName?.toUpperCase()}] compiled successfully.`, ...prev]);

          // Save partial result structures into Zustand store in real-time
          if (stageName === 'dna') saveDNA(projId, mapDnaResponse(result));
          else if (stageName === 'features') saveFeatures(projId, mapFeaturesResponse(result));
          else if (stageName === 'roadmap') saveRoadmap(projId, mapRoadmapResponse(result));
          else if (stageName === 'team') saveTeam(projId, mapTeamResponse(result));
          else if (stageName === 'swot') saveSWOT(projId, mapSwotResponse(result));
          else if (stageName === 'cost') saveCost(projId, mapCostResponse(result));
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
          setStreamLog(prev => [
            `${isFatal ? '❌' : '⚠️'} Stage [${stageName?.toUpperCase()}] ${isFatal ? 'FAILED' : 'warning'}: ${errMsg}`,
            ...prev
          ]);
        } catch (err) {
          console.error('module:failed parse error', err);
        }
      });

      es.addEventListener('workflow:completed', () => {
        const stageLabel = stage === 'blueprint' ? 'Final Blueprint' : `Stage [${stage.toUpperCase()}]`;
        setStreamLog(prev => [`🎉 ${stageLabel} compiled successfully!`, ...prev]);
        es.close();
        loadBlueprint(projId);
      });

      es.addEventListener('workflow:failed', (e: any) => {
        try {
          const data = JSON.parse(e.data);
          const errMsg = data.error_info?.error_message || 'Compilation failed';
          setStreamLog(prev => [`❌ Fatal error: ${errMsg}`, ...prev]);
          updateProjectStatus(projId, 'error');
          es.close();
        } catch (err) {
          console.error('workflow:failed parse error', err);
        }
      });

      es.onerror = (event) => {
        consecutiveErrors++;
        if (consecutiveErrors >= MAX_ERRORS) {
          setStreamLog(prev => ['❌ Stream connection lost. Generation may still be running in background.', ...prev]);
          es.close();
        } else {
          console.warn(`EventSource error #${consecutiveErrors} — retrying...`);
        }
      };

    } catch (err: any) {
      setStreamLog(prev => [`❌ Trigger failed: ${err.message}`, ...prev]);
      updateProjectStatus(projId, 'error');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;

    startTransition(async () => {
      try {
        const p = await createNewProject("Evolved Startup Idea", inputVal);
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

  // Safe loading check
  if (authLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-canvas">
        <div className="flex flex-col items-center gap-2">
          <RefreshCw className="h-6 w-6 text-accent-blue animate-spin" />
          <span className="text-xs text-muted-foreground">Authenticating session...</span>
        </div>
      </div>
    );
  }

  // Handle one-click complete pipeline generation
  const handleStartCompletePipeline = useCallback(async (projectId: string) => {
    const project = projects.find(p => p.id === projectId);
    if (!project) return;

    updateProjectStatus(projectId, 'generating');
    setStreamLog(['Starting complete venture blueprint generation...']);
    
    // Start the pipeline store
    usePipelineStore.getState().startPipeline(projectId);

    // Find first incomplete stage to start from
    const stagesToCheck = ['dna', 'features', 'roadmap', 'team', 'swot', 'cost'];
    let startStage = 'dna';
    
    for (const stage of stagesToCheck) {
      const frontendStage = getFrontendStageName(stage);
      if (!isStageCompleted(frontendStage, project)) {
        startStage = stage;
        break;
      }
    }

    // Start generation from the first incomplete stage
    await handleStartGeneration(projectId, startStage);
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
              onStageSelect={setActiveStage}
              onStartGeneration={handleStartGeneration}
              onStartCompletePipeline={handleStartCompletePipeline}
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
                        The AI pipeline encountered an error. This is often caused by Gemini API rate limits.
                        <br /><strong>Wait 1-2 minutes</strong> and retry — the system will automatically try backup models.
                      </p>
                      <div className="flex gap-2">
                        <Button
                          onClick={() => handleStartGeneration(activeProject.id, getBackendStageName(activeStage))}
                          className="gap-1.5 bg-red-600 hover:bg-red-700 text-white"
                        >
                          <RefreshCw className="h-4 w-4" />
                          <span>Retry Generation</span>
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => loadBlueprint(activeProject.id)}
                          className="gap-1.5"
                        >
                          <span>Load Partial Results</span>
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
                        Architecting Venture Blueprint...
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="skeleton h-4 w-3/4" />
                      <div className="skeleton h-4 w-1/2" />
                      <div className="skeleton h-32 w-full" />
                      <p className="text-sm text-muted-foreground">
                        AI models are working through each stage. This may take 2-5 minutes with rate limiting.
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
                          onClick={() => setActiveStage('final-blueprint')}
                          className="gap-1.5"
                        >
                          <span>Reveal Final Blueprint</span>
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
                            onClick={() => window.open(api.exports.pdf(activeProject.id), '_blank')}
                            className="gap-1.5"
                          >
                            Download PDF Package
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
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                          {(activeProject.financialIntelligence.unit_economics || []).map((item: any, idx: number) => (
                            <div key={idx} className="p-3 rounded-lg border border-border/60 bg-muted/50 text-center">
                              <span className="text-[10px] text-muted-foreground block">{item.metric}</span>
                              <span className="text-lg font-bold text-primary">{item.value}</span>
                              {item.benchmark && (
                                <span className="text-[10px] text-muted-foreground block">Bench: {item.benchmark}</span>
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
                                <th className="text-left py-2 font-semibold text-muted-foreground">Metric</th>
                                <th className="text-right py-2 font-semibold text-muted-foreground">Month 1</th>
                                <th className="text-right py-2 font-semibold text-muted-foreground">Month 6</th>
                                <th className="text-right py-2 font-semibold text-muted-foreground">Month 12</th>
                                <th className="text-right py-2 font-semibold text-muted-foreground">Month 24</th>
                              </tr>
                            </thead>
                            <tbody>
                              {(activeProject.financialIntelligence.projections || []).map((proj: any, idx: number) => (
                                <tr key={idx} className="border-b border-border/50">
                                  <td className="py-2 text-primary font-medium">{proj.metric}</td>
                                  <td className="py-2 text-right text-muted-foreground">{proj.month_1}</td>
                                  <td className="py-2 text-right text-muted-foreground">{proj.month_6}</td>
                                  <td className="py-2 text-right text-muted-foreground">{proj.month_12}</td>
                                  <td className="py-2 text-right text-muted-foreground">{proj.month_24}</td>
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
                        <p className="text-sm text-primary">{activeProject.investmentCommittee.investment_recommendation}</p>
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
                        <span>Launch Readiness: {activeProject.productExecution.launch_readiness}%</span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
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
                                <span className="text-xs font-semibold text-accent-blue">{arch.technology}</span>
                              </div>
                            ))}
                          </div>
                        </div>
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
