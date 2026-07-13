'use client';

import React, { useState, useEffect, useTransition } from 'react';
import { useBlueprintStore } from '@/store/use-blueprint-store';
import { useAuth } from '@/components/shared/auth-provider';
import { api, getAccessToken, mapDnaResponse, mapFeaturesResponse, mapRoadmapResponse, mapTeamResponse, mapSwotResponse, mapCostResponse } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { useSettingsStore } from '@/store/use-settings-store';
import { Sidebar } from '@/components/shared/sidebar';
import { Navbar } from '@/components/shared/navbar';
import { GlassPanel } from '@/components/shared/glass-panel';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
  Zap,
  Lock,
  Circle,
  Check,
  ChevronRight,
  BarChart3,
  Shield,
  DollarSign,
  FileText
} from 'lucide-react';
import { StageName } from '@/types/blueprint';

const getBackendStageName = (frontendStage: string): string => {
  const mapping: Record<string, string> = {
    'dna-analyzer': 'dna',
    'feature-extractor': 'features',
    'roadmap': 'roadmap',
    'team-structure': 'team',
    'swot': 'swot',
    'cost-estimator': 'cost',
    'final-blueprint': 'blueprint'
  };
  return mapping[frontendStage] || 'dna';
};

const isStageCompleted = (stage: StageName, project: any): boolean => {
  if (stage === 'dna-analyzer') return !!project.dna;
  if (stage === 'feature-extractor') return !!project.features;
  if (stage === 'roadmap') return !!project.roadmap;
  if (stage === 'team-structure') return !!project.team;
  if (stage === 'swot') return !!project.swot;
  if (stage === 'cost-estimator') return !!project.cost;
  if (stage === 'final-blueprint') return !!project.blueprintCompiled;
  return false;
};

/* =============================================
   STAGE PIPELINE CONFIG
   ============================================= */
const STAGES: { 
  name: StageName; 
  label: string; 
  shortLabel: string;
  icon: React.ComponentType<any>; 
  color: string; 
  glowClass: string;
  bgAccent: string;
}[] = [
  { name: 'dna-analyzer', label: 'Startup Blueprint', shortLabel: 'Startup Blueprint', icon: Dna, color: 'text-cyan-400', glowClass: 'glow-cyan', bgAccent: 'bg-cyan-500/10' },
  { name: 'feature-extractor', label: 'Feature Studio', shortLabel: 'Feature Studio', icon: GitBranch, color: 'text-violet-400', glowClass: 'glow-violet', bgAccent: 'bg-violet-500/10' },
  { name: 'roadmap', label: 'Launch Roadmap', shortLabel: 'Launch Roadmap', icon: LineChart, color: 'text-emerald-400', glowClass: 'glow-emerald', bgAccent: 'bg-emerald-500/10' },
  { name: 'team-structure', label: 'Team Builder', shortLabel: 'Team Builder', icon: Network, color: 'text-amber-400', glowClass: 'glow-amber', bgAccent: 'bg-amber-500/10' },
  { name: 'swot', label: 'Business Insights', shortLabel: 'Business Insights', icon: Shield, color: 'text-rose-400', glowClass: 'glow-rose', bgAccent: 'bg-rose-500/10' },
  { name: 'cost-estimator', label: 'Budget Planner', shortLabel: 'Budget Planner', icon: DollarSign, color: 'text-cyan-400', glowClass: 'glow-cyan', bgAccent: 'bg-cyan-500/10' },
  { name: 'final-blueprint', label: 'Final Draft', shortLabel: 'Final Draft', icon: FileText, color: 'text-violet-400', glowClass: 'glow-violet', bgAccent: 'bg-violet-500/10' },
];

/* =============================================
   SCORE RING SVG COMPONENT
   ============================================= */
function ScoreRing({ score, size = 80, label }: { score: number; size?: number; label?: string }) {
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} className="score-ring">
        <defs>
          <linearGradient id="score-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="hsl(192 91% 54%)" />
            <stop offset="100%" stopColor="hsl(262 83% 68%)" />
          </linearGradient>
        </defs>
        <circle className="track" cx={size/2} cy={size/2} r={radius} />
        <circle 
          className="fill" 
          cx={size/2} 
          cy={size/2} 
          r={radius}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ stroke: 'url(#score-gradient)' }}
        />
      </svg>
      <span className="text-lg font-bold text-foreground">{score}</span>
      {label && <span className="text-sm text-muted-foreground uppercase tracking-wider">{label}</span>}
    </div>
  );
}

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
    saveCost
  } = useBlueprintStore();

  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [inputVal, setInputVal] = useState('');
  const [startupName, setStartupName] = useState('');
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
        setStreamLog(prev => ["🚀 Pipeline running — generating startup blueprint...", ...prev]);
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
        const stageLabel = stage === 'blueprint' ? 'Final Draft' : `Stage [${stage.toUpperCase()}]`;
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
        const p = await createNewProject(startupName.trim() || "Evolved Startup Idea", inputVal);
        setInputVal('');
        setStartupName('');
        handleStartGeneration(p.id, 'dna');
      } catch (err) {
        console.error('Failed to evolve startup idea:', err);
      }
    });
  };

  const insertPrompt = (text: string) => {
    setInputVal(text);
  };

  // Get stage status for dock
  const getStageStatus = (stageName: StageName): 'completed' | 'active' | 'locked' | 'pending' => {
    if (!activeProject) return 'locked';
    if (isStageCompleted(stageName, activeProject)) return 'completed';
    if (activeStage === stageName) return 'active';
    
    const stageIdx = STAGES.findIndex(s => s.name === stageName);
    if (stageIdx === 0) return 'pending';
    
    const precedingStages = STAGES.slice(0, stageIdx);
    const allPrecedingDone = precedingStages.every(s => isStageCompleted(s.name, activeProject));
    return allPrecedingDone ? 'pending' : 'locked';
  };

  // Safe loading check
  if (authLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-mesh-dark">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-cyan-500/10 flex items-center justify-center glow-cyan">
            <RefreshCw className="h-5 w-5 text-cyan-400 animate-spin" />
          </div>
          <span className="text-sm text-muted-foreground">Authenticating session...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex overflow-hidden bg-mesh-dark font-sans select-none">
      {/* Sidebar Navigation */}
      <Sidebar />

      {/* Main Container Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <Navbar />

        {/* Focus Viewport */}
        <main className="flex-1 overflow-y-auto bg-mesh-dark relative">
          {!activeProject ? (
            /* =============================================
               CINEMATIC HERO — EMPTY STATE
               ============================================= */
            <div className="min-h-full flex flex-col items-center justify-center py-12 px-6 relative">
              {/* Floating Orbs */}
              <div className="absolute top-[15%] left-[10%] w-64 h-64 rounded-full bg-cyan-500/5 blur-[100px] float-orb pointer-events-none" />
              <div className="absolute bottom-[20%] right-[15%] w-48 h-48 rounded-full bg-violet-500/5 blur-[80px] float-orb-delayed pointer-events-none" />

              <div className="max-w-2xl w-full space-y-8 z-10">
                {/* Hero Title */}
                <div className="text-center space-y-3">
                  <h1 className="text-4xl font-bold tracking-tight">
                    <span className="gradient-text">Co-Author</span>
                    <span className="text-foreground"> Your Next Venture.</span>
                  </h1>
                  <p className="text-sm text-muted-foreground max-w-lg mx-auto leading-relaxed">
                    Describe a startup concept. Our AI engine will analyze market viability, structure product requirements, map timelines, and forecast runway costs.
                  </p>
                </div>

                {/* Prompt Input Box */}
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="relative rounded-xl border border-white/[0.08] bg-card/80 backdrop-blur-xl shadow-lvl-2 focus-within:border-cyan-500/30 focus-within:glow-cyan transition-all duration-300">
                    <input
                      value={startupName}
                      onChange={(e) => setStartupName(e.target.value)}
                      placeholder="Name of your startup (optional)"
                      className="w-full h-12 px-5 py-3 bg-transparent text-sm border-b border-white/[0.05] outline-none text-foreground font-semibold placeholder-muted-foreground/40"
                    />
                    <textarea
                      value={inputVal}
                      onChange={(e) => setInputVal(e.target.value)}
                      placeholder="Describe your startup idea in detail..."
                      className="w-full h-32 px-5 py-4 bg-transparent text-sm resize-none outline-none text-foreground placeholder-muted-foreground/40"
                    />
                    <div className="flex items-center justify-between px-4 py-3 border-t border-white/[0.05]">
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={handleEnhance}
                        disabled={isEnhancing || !inputVal}
                        className="h-8 text-sm gap-1.5 text-muted-foreground hover:text-cyan-400"
                      >
                        <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                        <span>{isEnhancing ? 'Enhancing...' : 'Enhance Idea'}</span>
                      </Button>
                      <Button
                        type="submit"
                        disabled={!inputVal.trim() || isPending}
                        className="h-9 text-sm gap-1.5 rounded-lg px-5"
                      >
                        <span>Evolve Idea</span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </form>

                {/* Starter Templates */}
                <div className="space-y-3">
                  <span className="text-sm font-semibold text-muted-foreground uppercase tracking-widest block text-center">
                    Starter Templates
                  </span>
                  <div className="flex flex-wrap gap-2 justify-center">
                    {[
                      "An AI-powered automated fitness coach for busy urban professionals",
                      "A localized peer-to-peer drone delivery marketplace for farms",
                      "A B2B SaaS analytics tracker measuring ESG compliance footprints"
                    ].map((tpl, i) => (
                      <button
                        key={i}
                        onClick={() => insertPrompt(tpl)}
                        className="px-3.5 py-2 rounded-lg border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05] hover:border-cyan-500/20 text-sm text-muted-foreground text-left transition-all max-w-[340px] truncate cursor-pointer"
                      >
                        {tpl}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Pipeline Preview */}
                <div className="pt-6 border-t border-white/[0.04]">
                  <span className="text-sm font-semibold text-muted-foreground uppercase tracking-widest block text-center mb-5">
                    AI Architecture Pipeline
                  </span>
                  <div className="flex items-center justify-center gap-2">
                    {STAGES.slice(0, 4).map((stage, i) => {
                      const Icon = stage.icon;
                      return (
                        <React.Fragment key={stage.name}>
                          <div className="flex flex-col items-center gap-2 px-3 py-3 rounded-xl border border-white/[0.06] bg-white/[0.02] min-w-[120px]">
                            <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center", stage.bgAccent)}>
                              <Icon className={cn("h-5 w-5", stage.color)} />
                            </div>
                            <span className="text-sm font-medium text-muted-foreground">{stage.shortLabel}</span>
                          </div>
                          {i < 3 && <ChevronRight className="h-5 w-5 text-white/10 shrink-0" />}
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* =============================================
               ACTIVE BLUEPRINT — COMMAND CENTER
               ============================================= */
            <div className="h-full flex flex-col">
              {/* Main Content Grid */}
              <div className="flex-1 flex gap-0 overflow-hidden">
                {/* Left Column: Stage Content */}
                <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
                  <div className="max-w-4xl space-y-6">
                    {/* ERROR STATE */}
                    {activeProject.status === 'error' && (
                      <div className="p-5 rounded-xl border border-rose-500/20 bg-rose-500/5 backdrop-blur-sm space-y-3">
                        <div className="flex items-center gap-2 text-rose-400">
                          <AlertTriangle className="h-5 w-5" />
                          <span className="text-sm font-semibold">Generation Failed</span>
                        </div>
                        <p className="text-sm text-rose-300/70 leading-relaxed">
                          The AI pipeline encountered an error. Wait 1-2 minutes and retry — the system will automatically try backup models.
                        </p>
                        <div className="flex gap-2">
                          <Button
                            onClick={() => handleStartGeneration(activeProject.id, getBackendStageName(activeStage))}
                            className="h-8 text-sm gap-1.5"
                          >
                            <RefreshCw className="h-3.5 w-3.5" />
                            <span>Retry Generation</span>
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => loadBlueprint(activeProject.id)}
                            className="h-8 text-sm gap-1.5"
                          >
                            <span>Load Partial Results</span>
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* GENERATING SKELETON */}
                    {activeProject.status === 'generating' && !isStageCompleted(activeStage, activeProject) && (
                      <div className="p-6 rounded-xl border border-white/[0.06] bg-card/60 backdrop-blur-sm space-y-5">
                        <div className="flex items-center gap-3">
                          <div className="h-2.5 w-2.5 rounded-full bg-cyan-400 animate-pulse" />
                          <span className="text-sm font-semibold text-foreground">Architecting Venture Blueprint...</span>
                        </div>
                        <div className="space-y-3">
                          <div className="h-4 skeleton-dark w-3/4" />
                          <div className="h-4 skeleton-dark w-1/2" />
                          <div className="h-32 skeleton-dark w-full" />
                        </div>
                        <p className="text-sm text-muted-foreground">
                          AI models are working through each stage. Check the AI Feed →
                        </p>
                      </div>
                    )}


                    {/* ========== STAGE: DNA ANALYZER ========== */}
                    {activeStage === 'dna-analyzer' && activeProject.dna && (
                      <div className="space-y-5">
                        {/* Header */}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="h-10 w-10 rounded-xl bg-cyan-500/10 flex items-center justify-center glow-cyan">
                              <Dna className="h-5 w-5 text-cyan-400" />
                            </div>
                            <div>
                              <h2 className="text-xl font-bold text-foreground">Startup Blueprint</h2>
                              <span className="text-sm text-muted-foreground">Market viability and strategic analysis</span>
                            </div>
                          </div>
                          <span className="badge-active text-sm font-semibold px-2.5 py-1 rounded-full">
                            {activeProject.dna.confidence}% Confidence
                          </span>
                        </div>

                        {/* Bento Overview Grid */}
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                          <div className="lg:col-span-1 p-5 rounded-2xl border border-white/[0.06] bg-white/[0.02] shadow-sm">
                            <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest block mb-2">Category</span>
                            <span className="text-sm font-medium text-foreground">{activeProject.dna.category}</span>
                          </div>
                          <div className="lg:col-span-2 p-5 rounded-2xl border border-white/[0.06] bg-white/[0.02] shadow-sm max-h-[160px] overflow-y-auto scrollbar-thin">
                            <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest block mb-2">Target Market</span>
                            <p className="text-sm text-muted-foreground/90 leading-relaxed whitespace-pre-wrap">{activeProject.dna.targetMarket}</p>
                          </div>
                          <div className="lg:col-span-3 p-5 rounded-2xl border border-white/[0.06] bg-white/[0.02] shadow-sm max-h-[250px] overflow-y-auto scrollbar-thin">
                            <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest block mb-3">Business Model</span>
                            <p className="text-sm text-muted-foreground/90 leading-relaxed whitespace-pre-wrap">{activeProject.dna.businessModel}</p>
                          </div>
                        </div>

                        {/* Score Metrics + Ring */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div className="space-y-3">
                            <span className="text-sm font-semibold text-muted-foreground uppercase tracking-widest block">
                              Strategic Score Vectors
                            </span>
                            {Object.entries(activeProject.dna.scores).map(([key, val]: any) => (
                              <div key={key} className="flex justify-between items-center text-sm border-b border-white/[0.04] pb-2">
                                <span className="capitalize text-muted-foreground">{key.replace('_', ' ')}</span>
                                <div className="flex items-center gap-2">
                                  <div className="w-24 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                                    <div 
                                      className="h-full rounded-full" 
                                      style={{ 
                                        width: `${val}%`,
                                        background: 'linear-gradient(90deg, hsl(192 91% 54%), hsl(262 83% 68%))' 
                                      }} 
                                    />
                                  </div>
                                  <span className="font-semibold text-foreground w-8 text-right">{val}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                          <div className="flex items-center justify-center">
                            <ScoreRing 
                              score={Math.round(Object.values(activeProject.dna.scores).reduce((a: any, b: any) => a + b, 0) / 6)} 
                              size={120}
                              label="Average"
                            />
                          </div>
                        </div>

                        {/* Tabbed Content */}
                        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-full">
                          <TabsList className="bg-white/[0.03] border border-white/[0.06]">
                            <TabsTrigger value="model" className="text-sm">Value Proposition</TabsTrigger>
                            <TabsTrigger value="target" className="text-sm">USP Differentiators</TabsTrigger>
                            <TabsTrigger value="usp" className="text-sm">Strategic Context</TabsTrigger>
                          </TabsList>
                          <TabsContent value="model" className="p-4 mt-2 rounded-xl bg-white/[0.02] border border-white/[0.05] text-sm leading-relaxed text-muted-foreground">
                            {activeProject.dna.valueProposition}
                          </TabsContent>
                          <TabsContent value="target" className="p-4 mt-2 rounded-xl bg-white/[0.02] border border-white/[0.05] text-sm leading-relaxed text-muted-foreground">
                            {activeProject.dna.usp}
                          </TabsContent>
                          <TabsContent value="usp" className="p-4 mt-2 rounded-xl bg-white/[0.02] border border-white/[0.05] text-sm leading-relaxed text-muted-foreground">
                            {activeProject.dna.summary}
                          </TabsContent>
                        </Tabs>

                        {/* Handoff */}
                        <div className="pt-4 border-t border-white/[0.04] flex justify-end">
                          <Button onClick={() => setActiveStage('feature-extractor')} className="h-9 text-sm gap-1.5">
                            <span>Proceed to Feature Extraction</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* DNA Empty State */}
                    {activeStage === 'dna-analyzer' && !activeProject.dna && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                      <div className="flex flex-col items-center justify-center text-center py-16 space-y-6">
                        <div className="h-16 w-16 rounded-2xl bg-cyan-500/10 flex items-center justify-center glow-cyan float-orb">
                          <Dna className="h-8 w-8 text-cyan-400" />
                        </div>
                        <div className="space-y-2 max-w-md">
                          <h3 className="text-lg font-bold text-foreground">Startup Blueprint</h3>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            Evaluate market viability, validate user demographics, map value propositions, and outline key competitive advantages.
                          </p>
                        </div>
                        <Button onClick={() => handleStartGeneration(activeProject.id, 'dna')} className="h-10 text-sm gap-2 px-6">
                          <Sparkles className="h-5 w-5" />
                          <span>Generate Startup Blueprint</span>
                        </Button>
                      </div>
                    )}

                    {/* ========== STAGE: FEATURE EXTRACTOR ========== */}
                    {activeStage === 'feature-extractor' && activeProject.features && (
                      <div className="space-y-5">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-xl bg-violet-500/10 flex items-center justify-center glow-violet">
                            <GitBranch className="h-5 w-5 text-violet-400" />
                          </div>
                          <div>
                            <h2 className="text-xl font-bold text-foreground">Feature Studio</h2>
                            <span className="text-sm text-muted-foreground">Product requirement document</span>
                          </div>
                        </div>

                        <div className="grid grid-cols-3 gap-3">
                          <div className="p-3.5 rounded-xl border border-white/[0.06] bg-white/[0.02] text-center">
                            <span className="text-sm text-muted-foreground block mb-1">Total Features</span>
                            <span className="text-xl font-bold text-foreground">{activeProject.features.totalFeatures}</span>
                          </div>
                          <div className="p-3.5 rounded-xl border border-white/[0.06] bg-white/[0.02] text-center">
                            <span className="text-sm text-muted-foreground block mb-1">MVP Selected</span>
                            <span className="text-xl font-bold text-cyan-400">{activeProject.features.mvpFeatureIds.length}</span>
                          </div>
                          <div className="p-3.5 rounded-xl border border-white/[0.06] bg-white/[0.02] text-center">
                            <span className="text-sm text-muted-foreground block mb-1">Complexity</span>
                            <span className="text-xl font-bold text-foreground capitalize">{activeProject.features.complexityScore}</span>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 gap-4 max-h-[450px] overflow-y-auto pr-2 scrollbar-thin">
                          {activeProject.features.features.map((feature: any, idx: number) => (
                            <div key={feature.id || feature.name || idx} className="p-5 rounded-xl border border-white/[0.06] bg-white/[0.02] shadow-sm hover:border-violet-500/30 transition-all flex flex-col gap-3">
                              <div className="flex items-start justify-between gap-4">
                                <span className="text-base font-bold text-foreground">{feature.name}</span>
                                <span className={cn(
                                  "text-[10px] font-bold uppercase px-2.5 py-1 rounded-full shrink-0",
                                  feature.priority === 'critical' ? 'badge-active' : 
                                  feature.priority === 'high' ? 'badge-pending' : 'badge-locked'
                                )}>
                                  {feature.priority}
                                </span>
                              </div>
                              <div className="pt-3 border-t border-white/[0.04]">
                                <p className="text-sm text-muted-foreground/90 leading-relaxed whitespace-pre-wrap">{feature.description}</p>
                              </div>
                            </div>
                          ))}
                        </div>

                        <div className="pt-4 border-t border-white/[0.04] flex justify-end">
                          <Button onClick={() => setActiveStage('roadmap')} className="h-9 text-sm gap-1.5">
                            <span>Generate Timeline Roadmap</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Feature Extractor Empty State */}
                    {activeStage === 'feature-extractor' && !activeProject.features && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                      <div className="flex flex-col items-center justify-center text-center py-16 space-y-6">
                        <div className="h-16 w-16 rounded-2xl bg-violet-500/10 flex items-center justify-center glow-violet float-orb">
                          <GitBranch className="h-8 w-8 text-violet-400" />
                        </div>
                        <div className="space-y-2 max-w-md">
                          <h3 className="text-lg font-bold text-foreground">Feature Studio</h3>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            Transform your startup concept into a structured Product Requirement Document (PRD), feature lists, and MVP scoped items.
                          </p>
                        </div>
                        <Button onClick={() => handleStartGeneration(activeProject.id, 'features')} className="h-10 text-sm gap-2 px-6">
                          <Sparkles className="h-5 w-5" />
                          <span>Extract MVP Features</span>
                        </Button>
                      </div>
                    )}

                    {/* ========== STAGE: ROADMAP ========== */}
                    {activeStage === 'roadmap' && activeProject.roadmap && (
                      <div className="space-y-5">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-xl bg-emerald-500/10 flex items-center justify-center glow-emerald">
                            <LineChart className="h-5 w-5 text-emerald-400" />
                          </div>
                          <div>
                            <h2 className="text-xl font-bold text-foreground">Launch Roadmap</h2>
                            <span className="text-sm text-muted-foreground">Comprehensive multi-phase execution strategy</span>
                          </div>
                        </div>

                        <div className="space-y-6 max-h-[500px] overflow-y-auto pr-2 scrollbar-thin">
                          {activeProject.roadmap.phases.map((phase: any, idx: number) => (
                            <div key={phase.phase_id || phase.id || phase.name || idx} className="p-5 rounded-xl border border-white/[0.06] bg-white/[0.02] shadow-sm space-y-4">
                              <div className="flex justify-between items-center border-b border-white/[0.04] pb-3">
                                <div className="flex items-center gap-3">
                                  <span className="h-6 w-6 rounded-full bg-emerald-500/15 text-emerald-400 text-xs font-bold flex items-center justify-center">{idx + 1}</span>
                                  <span className="text-base font-bold text-foreground">{phase.name}</span>
                                </div>
                                <span className="badge-completed text-xs font-bold px-3 py-1 rounded-full">
                                  {phase.duration_months} Months
                                </span>
                              </div>
                              
                              {phase.milestones && phase.milestones.length > 0 && (
                                <div className="bg-emerald-500/5 rounded-lg p-3 border border-emerald-500/10">
                                  <span className="text-xs font-bold text-emerald-400 uppercase tracking-widest block mb-2">Key Milestones</span>
                                  <ul className="space-y-1">
                                    {phase.milestones.map((ms: string, i: number) => (
                                      <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                                        <Check className="h-4 w-4 text-emerald-500/70 shrink-0 mt-0.5" />
                                        <span>{ms}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              <div className="space-y-3 pl-2 border-l-2 border-emerald-500/20">
                                {phase.tasks?.map((task: any, i: number) => (
                                  <div key={task.id || task.task_id || task.name || i} className="p-4 bg-white/[0.01] rounded-lg border border-white/[0.03] space-y-2 relative ml-3 transition-all hover:bg-white/[0.03]">
                                    <div className="absolute -left-[1.4rem] top-5 h-2.5 w-2.5 rounded-full bg-emerald-500 glow-emerald" />
                                    <div className="flex justify-between items-start gap-4">
                                      <span className="text-sm font-bold text-foreground">{task.title}</span>
                                      <span className="text-[10px] font-medium text-muted-foreground bg-white/[0.06] px-2 py-1 rounded shrink-0">{task.duration_weeks}w</span>
                                    </div>
                                    <p className="text-sm text-muted-foreground/80 leading-relaxed whitespace-pre-wrap">{task.description}</p>
                                    <div className="pt-2 flex flex-wrap gap-2">
                                      {task.assigned_role_id && (
                                        <span className="text-[10px] text-cyan-400 bg-cyan-400/10 px-2 py-1 rounded border border-cyan-400/20">{task.assigned_role_id}</span>
                                      )}
                                      {task.dependencies && task.dependencies.length > 0 && (
                                        <span className="text-[10px] text-amber-400 bg-amber-400/10 px-2 py-1 rounded border border-amber-400/20">Depends on: {task.dependencies.join(', ')}</span>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>

                        <div className="pt-4 border-t border-white/[0.04] flex justify-end">
                          <Button onClick={() => setActiveStage('team-structure')} className="h-9 text-sm gap-1.5">
                            <span>Define Team Hires</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Roadmap Empty State */}
                    {activeStage === 'roadmap' && !activeProject.roadmap && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                      <div className="flex flex-col items-center justify-center text-center py-16 space-y-6">
                        <div className="h-16 w-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center glow-emerald float-orb">
                          <LineChart className="h-8 w-8 text-emerald-400" />
                        </div>
                        <div className="space-y-2 max-w-md">
                          <h3 className="text-lg font-bold text-foreground">Launch Roadmap</h3>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            Translate your feature spec into a multi-phase, week-by-week development roadmap with task durations.
                          </p>
                        </div>
                        <Button onClick={() => handleStartGeneration(activeProject.id, 'roadmap')} className="h-10 text-sm gap-2 px-6">
                          <Sparkles className="h-5 w-5" />
                          <span>Generate Timeline Roadmap</span>
                        </Button>
                      </div>
                    )}

                    {/* ========== STAGE: TEAM STRUCTURE ========== */}
                    {activeStage === 'team-structure' && activeProject.team && (
                      <div className="space-y-5">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-xl bg-amber-500/10 flex items-center justify-center glow-amber">
                            <Network className="h-5 w-5 text-amber-400" />
                          </div>
                          <div>
                            <h2 className="text-xl font-bold text-foreground">Team Builder</h2>
                            <span className="text-sm text-muted-foreground">{activeProject.team.recommendedTeamSize} recommended roles</span>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[500px] overflow-y-auto pr-2 scrollbar-thin">
                          {activeProject.team.orgChart?.map((role: any, idx: number) => (
                            <div key={role.roleId || role.id || role.role || idx} className="p-5 rounded-xl border border-white/[0.06] bg-white/[0.02] shadow-sm flex flex-col gap-4 hover:border-amber-500/30 transition-all">
                              <div className="flex justify-between items-start gap-4">
                                <div>
                                  <span className="text-base font-bold text-foreground block">{role.title}</span>
                                  <span className="text-xs text-muted-foreground uppercase tracking-widest">{role.department.replace('_', ' ')}</span>
                                </div>
                                <div className="text-right shrink-0">
                                  <span className="text-sm font-bold text-amber-400 block">${role.estimatedSalaryUsd?.toLocaleString()}/yr</span>
                                  <span className="text-[10px] bg-amber-400/10 text-amber-400 px-2 py-0.5 rounded border border-amber-400/20">{role.hiringStage}</span>
                                </div>
                              </div>
                              
                              <div className="space-y-3 pt-3 border-t border-white/[0.04] flex-1">
                                <div>
                                  <span className="text-xs font-semibold text-foreground block mb-1">Responsibilities</span>
                                  <ul className="space-y-1">
                                    {role.responsibilities?.map((resp: string, i: number) => (
                                      <li key={i} className="text-xs text-muted-foreground leading-relaxed flex gap-2">
                                        <span className="text-amber-500/50 mt-0.5">•</span>
                                        <span>{resp}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                                <div>
                                  <span className="text-xs font-semibold text-foreground block mb-1">Required Skills</span>
                                  <div className="flex flex-wrap gap-1.5">
                                    {role.requiredSkills?.map((skill: string, i: number) => (
                                      <span key={i} className="text-[10px] text-muted-foreground bg-white/[0.04] px-1.5 py-0.5 rounded">{skill}</span>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>

                        <div className="pt-4 border-t border-white/[0.04] flex justify-end">
                          <Button onClick={() => setActiveStage('swot')} className="h-9 text-sm gap-1.5">
                            <span>Assess Strategic Risks</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Team Empty State */}
                    {activeStage === 'team-structure' && !activeProject.team && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                      <div className="flex flex-col items-center justify-center text-center py-16 space-y-6">
                        <div className="h-16 w-16 rounded-2xl bg-amber-500/10 flex items-center justify-center glow-amber float-orb">
                          <Network className="h-8 w-8 text-amber-400" />
                        </div>
                        <div className="space-y-2 max-w-md">
                          <h3 className="text-lg font-bold text-foreground">Team Builder</h3>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            Forecast hiring requirements, define team roles, allocate departments, and calculate monthly salaries.
                          </p>
                        </div>
                        <Button onClick={() => handleStartGeneration(activeProject.id, 'team')} className="h-10 text-sm gap-2 px-6">
                          <Sparkles className="h-5 w-5" />
                          <span>Plan Team Hires</span>
                        </Button>
                      </div>
                    )}

                    {/* ========== STAGE: SWOT ========== */}
                    {activeStage === 'swot' && activeProject.swot && (
                      <div className="space-y-5">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-xl bg-rose-500/10 flex items-center justify-center glow-rose">
                            <Shield className="h-5 w-5 text-rose-400" />
                          </div>
                          <div>
                            <h2 className="text-xl font-bold text-foreground">Business Insights</h2>
                            <span className="text-sm text-muted-foreground">Competitive intelligence matrix</span>
                          </div>
                        </div>

                        <div className="space-y-4 max-h-[550px] overflow-y-auto pr-2 scrollbar-thin">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {[
                              { label: 'S — Strengths', data: activeProject.swot.strengths, textClass: 'text-emerald-400', bgClass: 'bg-emerald-500/50' },
                              { label: 'W — Weaknesses', data: activeProject.swot.weaknesses, textClass: 'text-rose-400', bgClass: 'bg-rose-500/50' },
                              { label: 'O — Opportunities', data: activeProject.swot.opportunities, textClass: 'text-cyan-400', bgClass: 'bg-cyan-500/50' },
                              { label: 'T — Threats', data: activeProject.swot.threats, textClass: 'text-amber-400', bgClass: 'bg-amber-500/50' }
                            ].map(({ label, data, textClass, bgClass }) => (
                              <div key={label} className="p-5 rounded-xl border border-white/[0.06] bg-white/[0.02] shadow-sm flex flex-col gap-3 h-[250px]">
                                <span className={cn("text-sm font-bold tracking-widest block uppercase", textClass)}>{label}</span>
                                <div className="space-y-2 overflow-y-auto scrollbar-thin pr-1 flex-1">
                                  {data?.map((item: string, i: number) => (
                                    <div key={i} className="flex items-start gap-2">
                                      <div className={cn("h-1.5 w-1.5 rounded-full mt-2.5 shrink-0", bgClass)} />
                                      <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">{item}</p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                          
                          {activeProject.swot.mitigations && activeProject.swot.mitigations.length > 0 && (
                            <div className="p-5 rounded-xl border border-rose-500/20 bg-rose-500/[0.02] shadow-sm space-y-4">
                              <span className="text-sm font-bold text-rose-400 uppercase tracking-widest block">Threat Mitigations</span>
                              <div className="grid grid-cols-1 gap-3">
                                {activeProject.swot.mitigations.map((mit: any, i: number) => (
                                  <div key={i} className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                                    <div className="flex justify-between gap-4 mb-2">
                                      <span className="text-sm font-semibold text-foreground">{mit.threatDescription}</span>
                                      <span className="text-[10px] bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded shrink-0">Sev {mit.severity}</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground/90 leading-relaxed whitespace-pre-wrap">{mit.mitigationStrategy}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {activeProject.swot.founderActions && activeProject.swot.founderActions.length > 0 && (
                            <div className="p-5 rounded-xl border border-violet-500/20 bg-violet-500/[0.02] shadow-sm space-y-4">
                              <span className="text-sm font-bold text-violet-400 uppercase tracking-widest block">Founder Actions Timeline</span>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {activeProject.swot.founderActions.map((action: any, i: number) => (
                                  <div key={i} className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">{action.horizon.replace(/_/g, ' ')}</span>
                                    <p className="text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap">{action.action}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="pt-4 border-t border-white/[0.04] flex justify-end">
                          <Button onClick={() => setActiveStage('cost-estimator')} className="h-9 text-sm gap-1.5">
                            <span>Calculate Runway Costs</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* SWOT Empty State */}
                    {activeStage === 'swot' && !activeProject.swot && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                      <div className="flex flex-col items-center justify-center text-center py-16 space-y-6">
                        <div className="h-16 w-16 rounded-2xl bg-rose-500/10 flex items-center justify-center glow-rose float-orb">
                          <Shield className="h-8 w-8 text-rose-400" />
                        </div>
                        <div className="space-y-2 max-w-md">
                          <h3 className="text-lg font-bold text-foreground">Business Insights</h3>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            Analyze strategic Strengths, Weaknesses, Opportunities, and Threats to uncover business insights.
                          </p>
                        </div>
                        <Button onClick={() => handleStartGeneration(activeProject.id, 'swot')} className="h-10 text-sm gap-2 px-6">
                          <Sparkles className="h-5 w-5" />
                          <span>View Business Insights</span>
                        </Button>
                      </div>
                    )}

                    {/* ========== STAGE: COST ESTIMATOR ========== */}
                    {activeStage === 'cost-estimator' && activeProject.cost && (
                      <div className="space-y-5">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-xl bg-cyan-500/10 flex items-center justify-center glow-cyan">
                            <DollarSign className="h-5 w-5 text-cyan-400" />
                          </div>
                          <div>
                            <h2 className="text-xl font-bold text-foreground">Budget Planner</h2>
                            <span className="text-sm text-muted-foreground">Burn rate & runway analysis</span>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <div className="p-5 rounded-2xl border border-white/[0.06] bg-white/[0.02] text-center shadow-sm">
                            <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest block mb-1">MVP Estimate</span>
                            <span className="text-2xl font-bold text-foreground">{formatCost(activeProject.cost.mvp_cost_estimate)}</span>
                          </div>
                          <div className="p-5 rounded-2xl border border-white/[0.06] bg-white/[0.02] text-center shadow-sm">
                            <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest block mb-1">Year 1 OPEX</span>
                            <span className="text-2xl font-bold text-foreground">{formatCost(activeProject.cost.year_1_cost_estimate)}</span>
                          </div>
                          <div className="p-5 rounded-2xl border border-white/[0.06] bg-white/[0.02] text-center shadow-sm relative overflow-hidden">
                            <div className="absolute inset-0 bg-cyan-500/5 glow-cyan" />
                            <div className="relative">
                              <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest block mb-1">Optimal Funding Target</span>
                              <span className="text-2xl font-bold text-cyan-400">{formatCost(activeProject.cost.funding_requirements?.optimal_target_usd)}</span>
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div className="space-y-3">
                            <span className="text-sm font-semibold text-foreground uppercase tracking-widest block mb-4">Budget Scenarios</span>
                            <div className="grid grid-cols-1 gap-3 max-h-[350px] overflow-y-auto pr-1 scrollbar-thin">
                              {activeProject.cost.budget_scenarios?.map((scen: any, i: number) => (
                                <div key={i} className="p-4 rounded-xl border border-white/[0.06] bg-white/[0.02] flex flex-col gap-2 transition-all hover:bg-white/[0.04]">
                                  <div className="flex justify-between items-center">
                                    <span className="text-sm font-bold text-foreground block uppercase">{scen.name}</span>
                                    <span className="text-xs text-muted-foreground bg-white/[0.04] px-2 py-0.5 rounded">{scen.runway_months}m runway</span>
                                  </div>
                                  <span className="text-base font-bold text-cyan-400 block">{formatCost(scen.monthly_burn_usd)} / mo</span>
                                  <p className="text-xs text-muted-foreground/90 leading-relaxed whitespace-pre-wrap">{scen.description}</p>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="space-y-3">
                            <span className="text-sm font-semibold text-foreground uppercase tracking-widest block mb-4">Operational Costs</span>
                            <div className="grid grid-cols-1 gap-3 max-h-[350px] overflow-y-auto pr-1 scrollbar-thin">
                              {activeProject.cost.operational_costs?.map((op: any, i: number) => (
                                <div key={i} className="p-4 rounded-xl border border-white/[0.06] bg-white/[0.02] flex flex-col gap-2 transition-all hover:bg-white/[0.04]">
                                  <div className="flex justify-between items-start gap-4">
                                    <span className="text-sm font-bold text-foreground block">{op.category.replace(/_/g, ' ')}</span>
                                    <span className="text-sm font-bold text-amber-400 shrink-0">{formatCost(op.monthly_usd)}/mo</span>
                                  </div>
                                  <p className="text-xs text-muted-foreground/90 leading-relaxed whitespace-pre-wrap">{op.description}</p>
                                  {op.is_mvp_critical && (
                                    <span className="text-[10px] text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 px-2 py-0.5 rounded self-start mt-1">MVP Critical</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>

                        <div className="pt-4 border-t border-white/[0.04] flex justify-end">
                          <Button onClick={() => setActiveStage('final-blueprint')} className="h-9 text-sm gap-1.5">
                            <span>Reveal Final Draft</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Cost Empty State */}
                    {activeStage === 'cost-estimator' && !activeProject.cost && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                      <div className="flex flex-col items-center justify-center text-center py-16 space-y-6">
                        <div className="h-16 w-16 rounded-2xl bg-cyan-500/10 flex items-center justify-center glow-cyan float-orb">
                          <DollarSign className="h-8 w-8 text-cyan-400" />
                        </div>
                        <div className="space-y-2 max-w-md">
                          <h3 className="text-lg font-bold text-foreground">Budget Planner</h3>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            Model MVP costs, burn rates, runway forecasts, and funding requirements for lean, balanced, and aggressive scenarios.
                          </p>
                        </div>
                        <Button onClick={() => handleStartGeneration(activeProject.id, 'cost')} className="h-10 text-sm gap-2 px-6">
                          <Sparkles className="h-5 w-5" />
                          <span>Calculate Runway Costs</span>
                        </Button>
                      </div>
                    )}

                    {/* ========== STAGE: FINAL BLUEPRINT ========== */}
                    {activeStage === 'final-blueprint' && activeProject.blueprintCompiled && (
                      <div className="space-y-5">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-xl bg-violet-500/10 flex items-center justify-center glow-violet">
                            <FileText className="h-5 w-5 text-violet-400" />
                          </div>
                          <div>
                            <h2 className="text-xl font-bold text-foreground">Final Draft</h2>
                            <span className="text-sm text-muted-foreground">Investor-ready operating document</span>
                          </div>
                        </div>

                        <div className="p-10 rounded-2xl border border-dashed border-white/[0.08] bg-white/[0.02] flex flex-col items-center justify-center text-center space-y-5">
                          <div className="h-16 w-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center glow-emerald">
                            <Check className="h-8 w-8 text-emerald-400" />
                          </div>
                          <div className="space-y-2">
                            <span className="text-lg font-bold text-foreground block">Your Operating Blueprint is Complete</span>
                            <span className="text-sm text-muted-foreground">The compiled strategy plan has been generated. Ready for export.</span>
                          </div>
                          <div className="flex gap-3">
                            <Button
                              onClick={() => window.open(api.exports.pdf(activeProject.id), '_blank')}
                              className="h-9 text-sm gap-1.5 px-5"
                            >
                              Download PDF Package
                            </Button>
                            <Button
                              onClick={async () => {
                                try {
                                  const payload = await api.exports.share(activeProject.id);
                                  const url = `${window.location.origin}/shared/${payload.share_token}`;
                                  setStreamLog(prev => [`Generated shareable link: ${url}`, ...prev]);
                                  alert(`Investor link created: ${url}`);
                                } catch (err: any) {
                                  alert(`Failed to share: ${err.message}`);
                                }
                              }}
                              className="glass-btn border-border h-9 text-sm gap-1.5 px-5 text-foreground"
                            >
                              Share Secure Web View
                            </Button>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Blueprint Empty State */}
                    {activeStage === 'final-blueprint' && !activeProject.blueprintCompiled && activeProject.status !== 'generating' && activeProject.status !== 'error' && (
                      <div className="flex flex-col items-center justify-center text-center py-16 space-y-6">
                        <div className="h-16 w-16 rounded-2xl bg-violet-500/10 flex items-center justify-center glow-violet float-orb">
                          <FileText className="h-8 w-8 text-violet-400" />
                        </div>
                        <div className="space-y-2 max-w-md">
                          <h3 className="text-lg font-bold text-foreground">Final Draft</h3>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            Assemble all modules into an investor-ready, comprehensive operating blueprint with secure sharing and PDF export.
                          </p>
                        </div>
                        <Button onClick={() => handleStartGeneration(activeProject.id, 'blueprint')} className="h-10 text-sm gap-2 px-6">
                          <Sparkles className="h-5 w-5" />
                          <span>Compile Final Draft</span>
                        </Button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Right Column: AI Reasoning Feed */}
                <div className="w-[320px] shrink-0 border-l border-white/[0.04] bg-card/30 backdrop-blur-sm flex flex-col">
                  <div className="px-4 py-3 border-b border-white/[0.04] flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-cyan-400 animate-pulse" />
                    <span className="text-sm font-semibold text-foreground">AI Reasoning Feed</span>
                  </div>
                  <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
                    {streamLog.map((log, i) => (
                      <div key={i} className="flex gap-2 p-2 rounded-lg bg-white/[0.02] border border-white/[0.03]">
                        <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shrink-0 mt-1.5" />
                        <span className="text-sm leading-relaxed text-muted-foreground">{log}</span>
                      </div>
                    ))}
                    {streamLog.length === 0 && (
                      <span className="text-muted-foreground/80 italic text-center block pt-24 text-sm">
                        Ready to co-author.
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* =============================================
                 BOTTOM DOCK — PIPELINE STAGE CARDS
                 ============================================= */}
              <div className="px-4 py-3 border-t border-white/[0.04] bg-card/50 backdrop-blur-md">
                <div className="flex items-center gap-2 justify-center">
                  {STAGES.map((stage) => {
                    const status = getStageStatus(stage.name);
                    const Icon = stage.icon;
                    const isActive = activeStage === stage.name;
                    return (
                      <button
                        key={stage.name}
                        disabled={status === 'locked'}
                        onClick={() => setActiveStage(stage.name)}
                        className={cn(
                          "dock-card flex flex-col items-center gap-1.5 px-4 py-2.5 rounded-xl border cursor-pointer min-w-[80px]",
                          isActive && "border-cyan-500/30 bg-cyan-500/5 glow-cyan",
                          !isActive && status === 'completed' && "border-emerald-500/15 bg-emerald-500/5 hover:bg-emerald-500/8",
                          !isActive && status === 'pending' && "border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]",
                          !isActive && status === 'locked' && "border-white/[0.03] bg-white/[0.01] opacity-40 cursor-not-allowed"
                        )}
                      >
                        <div className="relative">
                          <Icon className={cn(
                            "h-5 w-5",
                            isActive ? stage.color : 
                            status === 'completed' ? 'text-emerald-400' : 
                            status === 'locked' ? 'text-muted-foreground/80' : 'text-muted-foreground'
                          )} />
                          {status === 'completed' && (
                            <div className="absolute -top-1 -right-1.5 h-2.5 w-2.5 rounded-full bg-emerald-500 border border-card flex items-center justify-center">
                              <Check className="h-1.5 w-1.5 text-white" />
                            </div>
                          )}
                        </div>
                        <span className={cn(
                          "text-sm font-medium",
                          isActive ? 'text-cyan-400' : 
                          status === 'completed' ? 'text-emerald-400/80' :
                          status === 'locked' ? 'text-muted-foreground/80' : 'text-muted-foreground'
                        )}>
                          {stage.shortLabel}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
