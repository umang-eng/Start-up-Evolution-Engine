'use client';

import React, { useState, useEffect, useTransition } from 'react';
import { useBlueprintStore } from '@/store/use-blueprint-store';
import { useAuth } from '@/components/shared/auth-provider';
import { api, getAccessToken, mapDnaResponse, mapFeaturesResponse, mapRoadmapResponse, mapTeamResponse, mapSwotResponse, mapCostResponse } from '@/lib/api-client';
import { cn } from '@/lib/utils';
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
  Plus
} from 'lucide-react';
import { StageName } from '@/types/blueprint';

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
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<'model' | 'target' | 'usp'>('model');
  const [selectedScenario, setSelectedScenario] = useState<'lean' | 'balanced' | 'aggressive'>('lean');
  const [isPending, startTransition] = useTransition();

  const activeProject = projects.find(p => p.id === activeProjectId);

  // Load projects from database on startup
  useEffect(() => {
    if (isAuthenticated) {
      loadProjects();
    }
  }, [isAuthenticated]);

  // Load compiled details if active project state is already completed but empty in store
  useEffect(() => {
    if (activeProject && activeProject.status === 'completed' && !activeProject.dna && activeProjectId) {
      loadBlueprint(activeProjectId);
    }
  }, [activeProjectId]);

  // Auto-enhance idea trigger
  const handleEnhance = () => {
    if (!inputVal) return;
    setIsEnhancing(true);
    setTimeout(() => {
      setInputVal(prev => prev + " targeting urban professionals, monetized via usage-based monthly subscription model with minimal hosting infrastructure.");
      setIsEnhancing(false);
    }, 1200);
  };

  // Run real generation sequence using Server-Sent Events (SSE)
  const handleStartGeneration = async (projId: string) => {
    updateProjectStatus(projId, 'generating');
    setStreamLog(["Contacting business intelligence diagnostics orchestrator..."]);

    const token = getAccessToken();
    if (!token) {
      setStreamLog(prev => ["Error: Authentication credentials missing", ...prev]);
      updateProjectStatus(projId, 'error');
      return;
    }

    try {
      // 1. Trigger Async execution run
      await api.generator.run(projId);
      setStreamLog(prev => ["Workflow generation triggered successfully. Launching streaming connection...", ...prev]);

      // 2. Open EventSource connection with token query param
      const eventSourceUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/streams/progress/${projId}?token=${encodeURIComponent(token)}`;
      const es = new EventSource(eventSourceUrl);

      es.addEventListener('workflow:started', () => {
        setStreamLog(prev => ["Pipeline running - Evolving startup DNA architecture...", ...prev]);
      });

      es.addEventListener('module:started', (e: any) => {
        try {
          const data = JSON.parse(e.data);
          const stageName = data.module_info?.module_name || '';
          setStreamLog(prev => [`Starting Stage [${stageName.toUpperCase()}]: Compiling dataset...`, ...prev]);
        } catch (err) {
          console.error(err);
        }
      });

      es.addEventListener('module:completed', (e: any) => {
        try {
          const data = JSON.parse(e.data);
          const stageName = data.module_info?.module_name;
          const result = data.result_info;

          setStreamLog(prev => [`Stage Completed: [${stageName.toUpperCase()}] compiled successfully.`, ...prev]);

          // Save partial result structures into Zustand store in real-time
          if (stageName === 'dna') {
            saveDNA(projId, mapDnaResponse(result));
          } else if (stageName === 'features') {
            saveFeatures(projId, mapFeaturesResponse(result));
          } else if (stageName === 'roadmap') {
            saveRoadmap(projId, mapRoadmapResponse(result));
          } else if (stageName === 'team') {
            saveTeam(projId, mapTeamResponse(result));
          } else if (stageName === 'swot') {
            saveSWOT(projId, mapSwotResponse(result));
          } else if (stageName === 'cost') {
            saveCost(projId, mapCostResponse(result));
          }
        } catch (err) {
          console.error('Failed to process streaming result payload:', err);
        }
      });

      es.addEventListener('workflow:completed', () => {
        setStreamLog(prev => ["🎉 Operating Blueprint Compiled successfully. Synchronizing state...", ...prev]);
        es.close();
        loadBlueprint(projId);
      });

      es.addEventListener('module:failed', (e: any) => {
        try {
          const data = JSON.parse(e.data);
          setStreamLog(prev => [`[Warning] Module execution failed: ${data.error_info?.error_message}`, ...prev]);
        } catch (err) {
          console.error(err);
        }
      });

      es.addEventListener('workflow:failed', (e: any) => {
        try {
          const data = JSON.parse(e.data);
          setStreamLog(prev => [`Fatal compilation error: ${data.error_info?.error_message}`, ...prev]);
          updateProjectStatus(projId, 'error');
          es.close();
        } catch (err) {
          console.error(err);
        }
      });

      es.onerror = () => {
        // EventSource will automatically retry connection if dropped
        console.warn('EventSource encountered connection interruption.');
      };

    } catch (err: any) {
      setStreamLog(prev => [`Orchestrator Trigger failed: ${err.message}`, ...prev]);
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
        handleStartGeneration(p.id);
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

  return (
    <div className="h-screen w-screen flex overflow-hidden bg-background font-sans select-none">
      {/* Sidebar Navigation */}
      <Sidebar />

      {/* Main Container Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <Navbar />

        {/* Focus Viewport */}
        <main className="flex-1 overflow-y-auto bg-canvas p-8">
          {!activeProject ? (
            /* INITIAL EMPTY STATE UI */
            <div className="max-w-3xl mx-auto py-12 space-y-10">
              {/* Welcome Banner */}
              <div className="space-y-3">
                <h1 className="text-3xl font-bold tracking-tight text-primary">
                  Co-Author Your Next Venture.
                </h1>
                <p className="text-sm text-muted-foreground max-w-xl leading-relaxed">
                  Provide a startup concept below. Our AI co-founder will analyze your market viability, structure product requirements, map development timelines, and forecast runway costs.
                </p>
              </div>

              {/* Startup Prompt Box Input */}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="relative rounded-lg border border-border bg-white shadow-lvl-1 focus-within:border-accent-blue transition-all">
                  <textarea
                    value={inputVal}
                    onChange={(e) => setInputVal(e.target.value)}
                    placeholder="Describe your startup idea in detail..."
                    className="w-full h-32 px-4 py-3 bg-transparent text-sm resize-none outline-none text-primary placeholder-muted-foreground/60"
                  />
                  <div className="flex items-center justify-between px-3 py-2 border-t border-border/60">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={handleEnhance}
                      disabled={isEnhancing || !inputVal}
                      className="h-8 text-xs gap-1.5 hover:bg-black/5 text-muted-foreground"
                    >
                      <Sparkles className="h-3.5 w-3.5 text-accent-blue" />
                      <span>{isEnhancing ? 'Enhancing...' : 'Enhance Idea'}</span>
                    </Button>
                    <Button
                      type="submit"
                      disabled={!inputVal.trim() || isPending}
                      className="h-8 text-xs gap-1.5 rounded-md px-4"
                    >
                      <span>Evolve Idea</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </form>

              {/* Prompt Suggestions Category Chips */}
              <div className="space-y-3">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                  Starter Templates
                </span>
                <div className="flex flex-wrap gap-2">
                  {[
                    "An AI-powered automated fitness coach for busy urban professionals",
                    "A localized peer-to-peer drone delivery marketplace for farms",
                    "A B2B SaaS analytics tracker measuring ESG compliance footprints"
                  ].map((tpl, i) => (
                    <button
                      key={i}
                      onClick={() => insertPrompt(tpl)}
                      className="px-3 py-1.5 rounded-md border border-border/80 bg-white hover:border-standard text-xs text-muted-foreground text-left transition-all max-w-[340px] truncate"
                    >
                      {tpl}
                    </button>
                  ))}
                </div>
              </div>

              {/* Workflow Roadmap Introduction */}
              <div className="pt-6 border-t border-border/50">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-4">
                  AI Architecture Pipeline
                </span>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { title: "1. DNA Analyzer", desc: "Viability metrics & target positioning." },
                    { title: "2. Feature Extractor", desc: "System PRD & dependency graphs." },
                    { title: "3. Timeline Roadmap", desc: "Phase milestones & project KPIs." },
                    { title: "4. Resource Org Plan", desc: "Team hierarchies & salaries." }
                  ].map((step, i) => (
                    <div key={i} className="p-4 rounded-lg border border-border/60 bg-white shadow-lvl-1">
                      <span className="text-xs font-semibold text-primary block mb-1">{step.title}</span>
                      <span className="text-[11px] text-muted-foreground leading-relaxed">{step.desc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* ACTIVE BLUEPRINT WORKSPACE */
            <div className="h-full flex gap-8">
              {/* Left Column: Canvas document display */}
              <div className="flex-1 max-w-4xl space-y-6">
                {/* Generation state skeletons */}
                {activeProject.status === 'generating' && (
                  <Card className="shadow-lvl-1 border-border bg-white animate-pulse">
                    <CardHeader>
                      <CardTitle className="text-lg font-semibold text-primary flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-accent-blue animate-pulse" />
                        Architecting Venture Blueprint Modules...
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="h-4 bg-black/5 rounded w-3/4" />
                      <div className="h-4 bg-black/5 rounded w-1/2" />
                      <div className="h-32 bg-black/5 rounded w-full" />
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: DNA ANALYZER */}
                {activeStage === 'dna-analyzer' && activeProject.dna && (
                  <Card className="shadow-lvl-1 border-border bg-white">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Business DNA Report
                      </CardTitle>
                      <div className="text-xs px-2.5 py-1 rounded bg-accent-blue/10 text-accent-blue font-medium flex items-center gap-1.5">
                        <Dna className="h-3.5 w-3.5" />
                        <span>Confidence {activeProject.dna.confidence}%</span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Overview grids */}
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 p-4 rounded-lg bg-surface-secondary border border-border/80 text-xs">
                        <div>
                          <span className="text-muted-foreground block mb-0.5">Category</span>
                          <span className="font-semibold text-primary">{activeProject.dna.category}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground block mb-0.5">Business Model</span>
                          <span className="font-semibold text-primary">{activeProject.dna.businessModel}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground block mb-0.5">Target Market</span>
                          <span className="font-semibold text-primary">{activeProject.dna.targetMarket}</span>
                        </div>
                      </div>

                      {/* Score metrics */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                        <div className="space-y-3">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                            Strategic Score Vectors
                          </span>
                          {Object.entries(activeProject.dna.scores).map(([key, val]: any) => (
                            <div key={key} className="flex justify-between items-center text-sm border-b border-border/50 pb-1.5">
                              <span className="capitalize text-muted-foreground">{key.replace('_', ' ')}</span>
                              <span className="font-semibold text-primary">{val}/100</span>
                            </div>
                          ))}
                        </div>
                        <div className="h-48 border border-border/60 rounded-lg bg-surface-secondary flex items-center justify-center relative overflow-hidden">
                          <div className="h-32 w-32 rounded-full border-2 border-accent-blue/20 flex items-center justify-center">
                            <div className="h-20 w-20 rounded-full border border-accent-blue flex items-center justify-center text-xs font-semibold text-accent-blue bg-white shadow-lvl-1">
                              {Math.round(Object.values(activeProject.dna.scores).reduce((a: any, b: any) => a + b, 0) / 6)} Avg
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Action tab lists */}
                      <div className="space-y-3">
                        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-full">
                          <TabsList className="bg-surface-secondary border border-border">
                            <TabsTrigger value="model" className="text-xs">Value Proposition</TabsTrigger>
                            <TabsTrigger value="target" className="text-xs">USP Differentiators</TabsTrigger>
                            <TabsTrigger value="usp" className="text-xs">Strategic Context</TabsTrigger>
                          </TabsList>
                          <TabsContent value="model" className="p-3 bg-surface-secondary/50 rounded-lg text-sm leading-relaxed text-muted-foreground border border-border/40">
                            {activeProject.dna.valueProposition}
                          </TabsContent>
                          <TabsContent value="target" className="p-3 bg-surface-secondary/50 rounded-lg text-sm leading-relaxed text-muted-foreground border border-border/40">
                            {activeProject.dna.usp}
                          </TabsContent>
                          <TabsContent value="usp" className="p-3 bg-surface-secondary/50 rounded-lg text-sm leading-relaxed text-muted-foreground border border-border/40">
                            {activeProject.dna.summary}
                          </TabsContent>
                        </Tabs>
                      </div>

                      {/* Handoff CTA */}
                      <div className="pt-4 border-t border-border/50 flex justify-end">
                        <Button 
                          onClick={() => setActiveStage('feature-extractor')}
                          className="h-8 text-xs gap-1.5"
                        >
                          <span>Proceed to Feature Extraction</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: FEATURE EXTRACTOR */}
                {activeStage === 'feature-extractor' && activeProject.features && (
                  <Card className="shadow-lvl-1 border-border bg-white">
                    <CardHeader>
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Feature Architecture Spec
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid grid-cols-3 gap-4 text-center p-4 bg-surface-secondary border border-border/80 rounded-lg">
                        <div>
                          <span className="text-[10px] text-muted-foreground block">Total Features</span>
                          <span className="text-lg font-bold text-primary">{activeProject.features.totalFeatures}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-muted-foreground block">MVP Selected</span>
                          <span className="text-lg font-bold text-accent-blue">{activeProject.features.mvpFeatureIds.length}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-muted-foreground block">Complexity Rating</span>
                          <span className="text-lg font-bold text-primary capitalize">{activeProject.features.complexityScore}</span>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                          Extracted Architecture
                        </span>
                        <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                          {activeProject.features.features.map((feature: any) => (
                            <div key={feature.id} className="p-3 rounded-lg border border-border/60 bg-white flex items-center justify-between hover:border-standard transition-all">
                              <div>
                                <span className="text-sm font-semibold text-primary block">{feature.name}</span>
                                <span className="text-xs text-muted-foreground leading-relaxed">{feature.description}</span>
                              </div>
                              <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-black/5 text-muted-foreground">
                                {feature.priority}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Handoff CTA */}
                      <div className="pt-4 border-t border-border/50 flex justify-end">
                        <Button 
                          onClick={() => setActiveStage('roadmap')}
                          className="h-8 text-xs gap-1.5"
                        >
                          <span>Generate Timeline Roadmap</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: ROADMAP */}
                {activeStage === 'roadmap' && activeProject.roadmap && (
                  <Card className="shadow-lvl-1 border-border bg-white">
                    <CardHeader>
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Timeline Execution Roadmap
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="space-y-4 max-h-[400px] overflow-y-auto pr-1">
                        {activeProject.roadmap.phases.map((phase: any) => (
                          <div key={phase.id} className="p-4 rounded-lg border border-border/60 bg-surface-secondary/50 space-y-3">
                            <div className="flex justify-between items-center">
                              <span className="text-sm font-semibold text-primary">{phase.name}</span>
                              <span className="text-xs text-accent-blue font-medium">Weeks {phase.startWeek} - {phase.endWeek}</span>
                            </div>
                            <div className="space-y-1.5 pl-3 border-l-2 border-accent-blue/30 text-xs">
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
                      <div className="pt-4 border-t border-border/50 flex justify-end">
                        <Button 
                          onClick={() => setActiveStage('team-structure')}
                          className="h-8 text-xs gap-1.5"
                        >
                          <span>Define Team Hires</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: TEAM STRUCTURE */}
                {activeStage === 'team-structure' && activeProject.team && (
                  <Card className="shadow-lvl-1 border-border bg-white">
                    <CardHeader>
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Resource Org Structure
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="space-y-3 max-h-[350px] overflow-y-auto pr-1">
                        {activeProject.team.roles.map((role: any) => (
                          <div key={role.id} className="p-4 rounded-lg border border-border/60 bg-white flex items-center justify-between hover:border-standard transition-all">
                            <div>
                              <span className="text-sm font-semibold text-primary block">{role.name}</span>
                              <span className="text-xs text-muted-foreground font-medium capitalize">{role.department.replace('_', ' ')} • Stage: {role.hiringStage}</span>
                            </div>
                            <span className="text-xs font-semibold text-accent-blue">
                              ${role.monthlyCost.toLocaleString()}/mo
                            </span>
                          </div>
                        ))}
                      </div>

                      {/* Handoff CTA */}
                      <div className="pt-4 border-t border-border/50 flex justify-end">
                        <Button 
                          onClick={() => setActiveStage('swot')}
                          className="h-8 text-xs gap-1.5"
                        >
                          <span>Assess Strategic Risks</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: SWOT ANALYSIS */}
                {activeStage === 'swot' && activeProject.swot && (
                  <Card className="shadow-lvl-1 border-border bg-white">
                    <CardHeader>
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Strategic SWOT Board
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid grid-cols-2 gap-4">
                        {/* Strengths */}
                        <div className="p-4 rounded-lg border border-border bg-surface-secondary/40 space-y-2">
                          <span className="text-xs font-bold text-primary block">S - Strengths</span>
                          <div className="space-y-1.5 text-xs text-muted-foreground max-h-[120px] overflow-y-auto">
                            {activeProject.swot.items.filter((i: any) => i.type === 'strength').map((item: any) => (
                              <div key={item.id}>• {item.content}</div>
                            ))}
                          </div>
                        </div>
                        {/* Weaknesses */}
                        <div className="p-4 rounded-lg border border-border bg-surface-secondary/40 space-y-2">
                          <span className="text-xs font-bold text-primary block">W - Weaknesses</span>
                          <div className="space-y-1.5 text-xs text-muted-foreground max-h-[120px] overflow-y-auto">
                            {activeProject.swot.items.filter((i: any) => i.type === 'weakness').map((item: any) => (
                              <div key={item.id}>• {item.content}</div>
                            ))}
                          </div>
                        </div>
                        {/* Opportunities */}
                        <div className="p-4 rounded-lg border border-border bg-surface-secondary/40 space-y-2">
                          <span className="text-xs font-bold text-primary block">O - Opportunities</span>
                          <div className="space-y-1.5 text-xs text-muted-foreground max-h-[120px] overflow-y-auto">
                            {activeProject.swot.items.filter((i: any) => i.type === 'opportunity').map((item: any) => (
                              <div key={item.id}>• {item.content}</div>
                            ))}
                          </div>
                        </div>
                        {/* Threats */}
                        <div className="p-4 rounded-lg border border-border bg-surface-secondary/40 space-y-2">
                          <span className="text-xs font-bold text-primary block">T - Threats</span>
                          <div className="space-y-1.5 text-xs text-muted-foreground max-h-[120px] overflow-y-auto">
                            {activeProject.swot.items.filter((i: any) => i.type === 'threat').map((item: any) => (
                              <div key={item.id}>• {item.content}</div>
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* Handoff CTA */}
                      <div className="pt-4 border-t border-border/50 flex justify-end">
                        <Button 
                          onClick={() => setActiveStage('cost-estimator')}
                          className="h-8 text-xs gap-1.5"
                        >
                          <span>Calculate Runway Costs</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: COST ESTIMATOR */}
                {activeStage === 'cost-estimator' && activeProject.cost && (
                  <Card className="shadow-lvl-1 border-border bg-white">
                    <CardHeader>
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Startup Financial Projections
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid grid-cols-3 gap-4 text-center p-4 bg-surface-secondary border border-border/80 rounded-lg">
                        <div>
                          <span className="text-[10px] text-muted-foreground block">Estimated MVP Cost</span>
                          <span className="text-lg font-bold text-primary">${activeProject.cost.mvpCost.toLocaleString()}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-muted-foreground block">Year 1 Projection</span>
                          <span className="text-lg font-bold text-primary">${activeProject.cost.year1Cost.toLocaleString()}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-muted-foreground block">Funding Required</span>
                          <span className="text-lg font-bold text-accent-blue">${activeProject.cost.fundingRequirement.toLocaleString()}</span>
                        </div>
                      </div>

                      <div className="space-y-3">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                          Budget Scenarios Simulator
                        </span>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          {activeProject.cost.scenarios.map((scen: any) => (
                            <button
                              key={scen.id}
                              onClick={() => setSelectedScenario(scen.id)}
                              className={cn(
                                "p-4 rounded-lg border text-left transition-all space-y-2",
                                selectedScenario === scen.id 
                                  ? "border-accent-blue bg-accent-foreground/5 shadow-lvl-1" 
                                  : "border-border/60 bg-white hover:border-standard"
                              )}
                            >
                              <span className="text-xs font-bold text-primary block uppercase">{scen.name}</span>
                              <span className="text-lg font-bold text-accent-blue block">${scen.mvpCost.toLocaleString()} MVP</span>
                              <span className="text-[11px] text-muted-foreground leading-relaxed block">{scen.description}</span>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Handoff CTA */}
                      <div className="pt-4 border-t border-border/50 flex justify-end">
                        <Button 
                          onClick={() => setActiveStage('final-blueprint')}
                          className="h-8 text-xs gap-1.5"
                        >
                          <span>Reveal Final Blueprint</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE: FINAL BLUEPRINT */}
                {activeStage === 'final-blueprint' && (
                  <Card className="shadow-lvl-1 border-border bg-white">
                    <CardHeader>
                      <CardTitle className="text-xl font-bold tracking-tight text-primary">
                        Compiled Startup Blueprint
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="p-8 rounded-xl border border-dashed border-border bg-surface-secondary flex flex-col items-center justify-center text-center space-y-4">
                        <div className="h-12 w-12 rounded-full bg-accent-blue/10 flex items-center justify-center text-accent-blue font-bold">
                          ✓
                        </div>
                        <div className="space-y-1">
                          <span className="text-base font-bold text-primary block">Your Operating Blueprint is Complete</span>
                          <span className="text-xs text-muted-foreground">The compiled strategy plan has been generated and validated. Ready for export.</span>
                        </div>
                        <div className="flex gap-2">
                          <Button 
                            onClick={() => window.open(api.exports.pdf(activeProject.id), '_blank')}
                            className="h-8 text-xs"
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
              </div>

              {/* Right Column: AI Reasoning copilot stream */}
              <div className="w-[320px] shrink-0 space-y-6">
                <GlassPanel shadow="lvl-2" className="p-4 bg-white/70 h-[480px] flex flex-col">
                  <span className="text-xs font-semibold text-primary flex items-center gap-1.5 mb-3 border-b border-border/60 pb-2">
                    <Sparkles className="h-4 w-4 text-accent-blue animate-pulse" />
                    AI Reasoning Feed
                  </span>

                  {/* Streaming logs list */}
                  <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 text-[11px] leading-relaxed text-muted-foreground scrollbar-thin">
                    {streamLog.map((log, i) => (
                      <div key={i} className="flex gap-2 p-1.5 rounded bg-black/5">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent-blue shrink-0 mt-1.5" />
                        <span>{log}</span>
                      </div>
                    ))}
                    {streamLog.length === 0 && (
                      <span className="text-muted-foreground/50 italic text-center block pt-24">
                        Ready to co-author.
                      </span>
                    )}
                  </div>
                </GlassPanel>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
