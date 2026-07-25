'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Mic,
  FileText,
  BarChart3,
  ArrowLeft,
  Loader2,
  Sparkles,
  Brain,
  Zap,
  Heart,
  Clock,
  Layers,
} from 'lucide-react';
import { AudioRecorder, TranscriptUploader, ReportViewer, MeetingsList } from '@/components/meetings';
import { useMeetingStore } from '@/store/use-meeting-store';
import { cn } from '@/lib/utils';

export default function MeetingsPage() {
  const router = useRouter();
  const {
    currentMeeting,
    transcript,
    report,
    health,
    timeline,
    analysis,
    generating,
    analyzingHealth,
    analyzingTimeline,
    analyzingCombined,
    selectMeeting,
    generateReport,
    fetchHealth,
    fetchTimeline,
    runAnalysis,
    clearCurrent,
  } = useMeetingStore();

  const [activeTab, setActiveTab] = useState('record');
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);

  const handleSelectMeeting = async (meetingId: string) => {
    setSelectedMeetingId(meetingId);
    await selectMeeting(meetingId);
    if (currentMeeting?.status === 'TRANSCRIBED' || currentMeeting?.status === 'ANALYZED') {
      setActiveTab('report');
    }
  };

  const handleRecordComplete = async (meetingId: string) => {
    setSelectedMeetingId(meetingId);
    await selectMeeting(meetingId);
    setActiveTab('report');
  };

  const handleGenerateReport = async () => {
    if (!selectedMeetingId) return;
    try {
      await generateReport(selectedMeetingId);
    } catch (err) {
      // Error handled by store
    }
  };

  const handleFetchHealth = async () => {
    if (!selectedMeetingId) return;
    await fetchHealth(selectedMeetingId);
  };

  const handleFetchTimeline = async () => {
    if (!selectedMeetingId) return;
    await fetchTimeline(selectedMeetingId);
  };

  const handleRunAnalysis = async () => {
    if (!selectedMeetingId) return;
    await runAnalysis(selectedMeetingId);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-50 dark:from-slate-950 dark:via-indigo-950/20 dark:to-slate-950">
      {/* Header */}
      <div className="sticky top-0 z-10 backdrop-blur-xl bg-white/80 dark:bg-slate-950/80 border-b border-slate-200/60 dark:border-slate-800/60">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                onClick={() => router.back()}
                variant="ghost"
                size="sm"
                className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back
              </Button>
              <div className="h-6 w-px bg-slate-200 dark:bg-slate-800" />
              <div>
                <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
                  <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-purple-500/25">
                    <Brain className="h-4 w-4 text-white" />
                  </div>
                  Conversation Intelligence
                </h1>
                <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
                  Record, transcribe, and extract actionable insights from meetings
                </p>
              </div>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
              <Zap className="h-3.5 w-3.5" />
              <span>Powered by Whisper + AI</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Sidebar - Meeting History */}
          <div className="lg:col-span-4 xl:col-span-3">
            <MeetingsList onSelectMeeting={handleSelectMeeting} />
          </div>

          {/* Main Panel */}
          <div className="lg:col-span-8 xl:col-span-9">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="w-full justify-start bg-slate-100/80 dark:bg-slate-900/80 p-1 rounded-xl flex-wrap">
                <TabsTrigger
                  value="record"
                  className="flex-1 sm:flex-none data-[state=active]:bg-white dark:data-[state=active]:bg-slate-800 data-[state=active]:shadow-sm data-[state=active]:text-slate-900 dark:data-[state=active]:text-white rounded-lg transition-all"
                >
                  <Mic className="h-4 w-4 mr-1.5" />
                  Record
                </TabsTrigger>
                <TabsTrigger
                  value="upload"
                  className="flex-1 sm:flex-none data-[state=active]:bg-white dark:data-[state=active]:bg-slate-800 data-[state=active]:shadow-sm data-[state=active]:text-slate-900 dark:data-[state=active]:text-white rounded-lg transition-all"
                >
                  <FileText className="h-4 w-4 mr-1.5" />
                  Upload
                </TabsTrigger>
                <TabsTrigger
                  value="report"
                  className="flex-1 sm:flex-none data-[state=active]:bg-white dark:data-[state=active]:bg-slate-800 data-[state=active]:shadow-sm data-[state=active]:text-slate-900 dark:data-[state=active]:text-white rounded-lg transition-all"
                >
                  <Sparkles className="h-4 w-4 mr-1.5" />
                  Report
                </TabsTrigger>
                <TabsTrigger
                  value="health"
                  className="flex-1 sm:flex-none data-[state=active]:bg-white dark:data-[state=active]:bg-slate-800 data-[state=active]:shadow-sm data-[state=active]:text-slate-900 dark:data-[state=active]:text-white rounded-lg transition-all"
                >
                  <Heart className="h-4 w-4 mr-1.5" />
                  Health
                </TabsTrigger>
                <TabsTrigger
                  value="timeline"
                  className="flex-1 sm:flex-none data-[state=active]:bg-white dark:data-[state=active]:bg-slate-800 data-[state=active]:shadow-sm data-[state=active]:text-slate-900 dark:data-[state=active]:text-white rounded-lg transition-all"
                >
                  <Clock className="h-4 w-4 mr-1.5" />
                  Timeline
                </TabsTrigger>
                <TabsTrigger
                  value="combined"
                  className="flex-1 sm:flex-none data-[state=active]:bg-white dark:data-[state=active]:bg-slate-800 data-[state=active]:shadow-sm data-[state=active]:text-slate-900 dark:data-[state=active]:text-white rounded-lg transition-all"
                >
                  <Layers className="h-4 w-4 mr-1.5" />
                  Combined
                </TabsTrigger>
              </TabsList>

              <div className="mt-4">
                <TabsContent value="record" className="mt-0">
                  <AudioRecorder onComplete={handleRecordComplete} />
                </TabsContent>

                <TabsContent value="upload" className="mt-0">
                  {selectedMeetingId ? (
                    <TranscriptUploader
                      meetingId={selectedMeetingId}
                      onComplete={() => selectMeeting(selectedMeetingId)}
                    />
                  ) : (
                    <Card className="border-dashed border-2 border-slate-200 dark:border-slate-800 bg-transparent">
                      <CardContent className="p-16 text-center">
                        <div className="flex items-center justify-center h-16 w-16 rounded-2xl bg-slate-100 dark:bg-slate-900 mx-auto mb-4">
                          <FileText className="h-7 w-7 text-slate-300 dark:text-slate-600" />
                        </div>
                        <p className="text-slate-600 dark:text-slate-400 font-medium">Select a meeting first</p>
                        <p className="text-slate-400 dark:text-slate-500 text-sm mt-1.5 max-w-xs mx-auto">
                          Choose a meeting from the history panel to upload a transcript
                        </p>
                      </CardContent>
                    </Card>
                  )}
                </TabsContent>

                <TabsContent value="report" className="mt-0">
                  <ReportViewer
                    onGenerate={handleGenerateReport}
                    generating={generating}
                  />
                </TabsContent>

                {/* Health Dashboard Tab */}
                <TabsContent value="health" className="mt-0">
                  {selectedMeetingId ? (
                    <Card className="shadow-lvl-1 border-border bg-white">
                      <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-lg font-bold text-primary flex items-center gap-2">
                          <Heart className="h-5 w-5 text-accent-blue" />
                          Meeting Health Analysis
                        </CardTitle>
                        <Button 
                          onClick={handleFetchHealth} 
                          disabled={analyzingHealth}
                          variant="outline" 
                          size="sm"
                        >
                          {analyzingHealth ? (
                            <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                          ) : (
                            <Sparkles className="h-4 w-4 mr-1.5" />
                          )}
                          {analyzingHealth ? 'Analyzing...' : 'Analyze Health'}
                        </Button>
                      </CardHeader>
                      <CardContent>
                        {health ? (
                          <div className="space-y-6">
                            {/* Overall Score */}
                            <div className="text-center p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border border-blue-100">
                              <div className="text-5xl font-bold text-primary mb-2">
                                {health.overall_score.toFixed(1)}
                              </div>
                              <div className="text-sm text-muted-foreground">Overall Health Score</div>
                            </div>

                            {/* Dimensions Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                              {(health.dimensions || []).map((dim, idx) => (
                                <div key={idx} className="p-4 rounded-lg border border-border bg-surface-secondary/50">
                                  <div className="flex justify-between items-center mb-2">
                                    <span className="text-xs font-semibold text-primary">{dim.name}</span>
                                    <span className="text-sm font-bold text-accent-blue">{dim.score.toFixed(1)}</span>
                                  </div>
                                  <div className="h-2 bg-black/5 rounded-full overflow-hidden mb-2">
                                    <div 
                                      className={cn(
                                        "h-full rounded-full transition-all",
                                        dim.score >= 7 ? 'bg-green-500' :
                                        dim.score >= 5 ? 'bg-yellow-500' : 'bg-red-500'
                                      )}
                                      style={{ width: `${dim.score * 10}%` }}
                                    />
                                  </div>
                                  <p className="text-[10px] text-muted-foreground">{dim.explanation}</p>
                                  {dim.improvement && (
                                    <p className="text-[10px] text-accent-blue mt-1">💡 {dim.improvement}</p>
                                  )}
                                </div>
                              ))}
                            </div>

                            {/* Strengths & Weaknesses */}
                            <div className="grid grid-cols-2 gap-4">
                              <div className="p-4 rounded-lg border border-green-200 bg-green-50/50">
                                <span className="text-xs font-semibold text-green-700 block mb-2">Strengths</span>
                                <ul className="space-y-1">
                                  {(health.strengths || []).map((s, idx) => (
                                    <li key={idx} className="text-xs text-green-600">✓ {s}</li>
                                  ))}
                                </ul>
                              </div>
                              <div className="p-4 rounded-lg border border-yellow-200 bg-yellow-50/50">
                                <span className="text-xs font-semibold text-yellow-700 block mb-2">Weaknesses</span>
                                <ul className="space-y-1">
                                  {(health.weaknesses || []).map((w, idx) => (
                                    <li key={idx} className="text-xs text-yellow-600">⚠ {w}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="text-center py-12">
                            <Heart className="h-12 w-12 text-slate-200 mx-auto mb-4" />
                            <p className="text-slate-500 font-medium">No health analysis yet</p>
                            <p className="text-slate-400 text-sm mt-1">
                              Click "Analyze Health" to score this meeting across 9 dimensions
                            </p>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ) : (
                    <Card className="border-dashed border-2 border-slate-200 bg-transparent">
                      <CardContent className="p-16 text-center">
                        <Heart className="h-12 w-12 text-slate-200 mx-auto mb-4" />
                        <p className="text-slate-500 font-medium">Select a meeting first</p>
                      </CardContent>
                    </Card>
                  )}
                </TabsContent>

                {/* Timeline Tab */}
                <TabsContent value="timeline" className="mt-0">
                  {selectedMeetingId ? (
                    <Card className="shadow-lvl-1 border-border bg-white">
                      <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-lg font-bold text-primary flex items-center gap-2">
                          <Clock className="h-5 w-5 text-accent-blue" />
                          Startup Timeline Events
                        </CardTitle>
                        <Button 
                          onClick={handleFetchTimeline} 
                          disabled={analyzingTimeline}
                          variant="outline" 
                          size="sm"
                        >
                          {analyzingTimeline ? (
                            <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                          ) : (
                            <Sparkles className="h-4 w-4 mr-1.5" />
                          )}
                          {analyzingTimeline ? 'Extracting...' : 'Extract Events'}
                        </Button>
                      </CardHeader>
                      <CardContent>
                        {timeline.length > 0 ? (
                          <div className="space-y-3">
                            {timeline.map((event, idx) => (
                              <div key={idx} className="flex gap-4 p-4 rounded-lg border border-border bg-surface-secondary/50">
                                <div className={cn(
                                  "h-10 w-10 rounded-lg flex items-center justify-center shrink-0",
                                  event.importance === 'critical' ? 'bg-red-100 text-red-600' :
                                  event.importance === 'high' ? 'bg-orange-100 text-orange-600' :
                                  event.importance === 'medium' ? 'bg-blue-100 text-blue-600' :
                                  'bg-gray-100 text-gray-600'
                                )}>
                                  <Clock className="h-5 w-5" />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="text-sm font-semibold text-primary">{event.title}</span>
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 uppercase">
                                      {event.event_type.replace('_', ' ')}
                                    </span>
                                  </div>
                                  <p className="text-xs text-muted-foreground">{event.description}</p>
                                  {event.affected_areas?.length > 0 && (
                                    <div className="flex gap-1.5 mt-2">
                                      {event.affected_areas.map((area, aIdx) => (
                                        <span key={aIdx} className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">
                                          {area}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center py-12">
                            <Clock className="h-12 w-12 text-slate-200 mx-auto mb-4" />
                            <p className="text-slate-500 font-medium">No timeline events extracted</p>
                            <p className="text-slate-400 text-sm mt-1">
                              Click "Extract Events" to pull timeline-worthy events from this meeting
                            </p>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ) : (
                    <Card className="border-dashed border-2 border-slate-200 bg-transparent">
                      <CardContent className="p-16 text-center">
                        <Clock className="h-12 w-12 text-slate-200 mx-auto mb-4" />
                        <p className="text-slate-500 font-medium">Select a meeting first</p>
                      </CardContent>
                    </Card>
                  )}
                </TabsContent>

                {/* Combined Analysis Tab */}
                <TabsContent value="combined" className="mt-0">
                  {selectedMeetingId ? (
                    <Card className="shadow-lvl-1 border-border bg-white">
                      <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-lg font-bold text-primary flex items-center gap-2">
                          <Layers className="h-5 w-5 text-accent-blue" />
                          Combined Intelligence Analysis
                        </CardTitle>
                        <Button 
                          onClick={handleRunAnalysis} 
                          disabled={analyzingCombined}
                          variant="outline" 
                          size="sm"
                        >
                          {analyzingCombined ? (
                            <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                          ) : (
                            <Sparkles className="h-4 w-4 mr-1.5" />
                          )}
                          {analyzingCombined ? 'Running...' : 'Run Full Analysis'}
                        </Button>
                      </CardHeader>
                      <CardContent>
                        {analysis ? (
                          <div className="space-y-6">
                            {/* Health Summary */}
                            <div className="p-4 rounded-lg border border-border bg-surface-secondary/50">
                              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-3">
                                Health Summary
                              </span>
                              <div className="flex items-center gap-4">
                                <div className="text-3xl font-bold text-primary">
                                  {analysis.health?.overall_score?.toFixed(1) || 'N/A'}
                                </div>
                                <div className="flex-1">
                                  <div className="flex gap-2">
                                    {(analysis.health?.dimensions || []).slice(0, 4).map((dim, idx) => (
                                      <span key={idx} className="text-[10px] px-2 py-1 rounded bg-white border border-border">
                                        {dim.name}: {dim.score.toFixed(1)}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Timeline Summary */}
                            <div className="p-4 rounded-lg border border-border bg-surface-secondary/50">
                              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-3">
                                Timeline Events ({analysis.timeline?.total_events || 0})
                              </span>
                              <div className="space-y-2">
                                {(analysis.timeline?.events || []).slice(0, 5).map((event, idx) => (
                                  <div key={idx} className="flex items-center gap-2 text-xs">
                                    <span className="h-2 w-2 rounded-full bg-accent-blue shrink-0" />
                                    <span className="text-primary font-medium">{event.title}</span>
                                    <span className="text-muted-foreground">— {event.event_type}</span>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Report Summary */}
                            {report && (
                              <div className="p-4 rounded-lg border border-border bg-surface-secondary/50">
                                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-3">
                                  Report Summary
                                </span>
                                {report.executive_summary && (
                                  <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
                                    {report.executive_summary}
                                  </p>
                                )}
                                <div className="flex gap-4 mt-3">
                                  <span className="text-xs text-muted-foreground">
                                    {report.key_points?.length || 0} key points
                                  </span>
                                  <span className="text-xs text-muted-foreground">
                                    {report.decisions?.length || 0} decisions
                                  </span>
                                  <span className="text-xs text-muted-foreground">
                                    {report.action_items?.length || 0} action items
                                  </span>
                                </div>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="text-center py-12">
                            <Layers className="h-12 w-12 text-slate-200 mx-auto mb-4" />
                            <p className="text-slate-500 font-medium">No combined analysis yet</p>
                            <p className="text-slate-400 text-sm mt-1">
                              Click "Run Full Analysis" to merge health, timeline, and report insights
                            </p>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ) : (
                    <Card className="border-dashed border-2 border-slate-200 bg-transparent">
                      <CardContent className="p-16 text-center">
                        <Layers className="h-12 w-12 text-slate-200 mx-auto mb-4" />
                        <p className="text-slate-500 font-medium">Select a meeting first</p>
                      </CardContent>
                    </Card>
                  )}
                </TabsContent>
              </div>
            </Tabs>
          </div>
        </div>
      </div>
    </div>
  );
}
