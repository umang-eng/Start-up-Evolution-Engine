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
} from 'lucide-react';
import { AudioRecorder, TranscriptUploader, ReportViewer, MeetingsList } from '@/components/meetings';
import { useMeetingStore } from '@/store/use-meeting-store';

export default function MeetingsPage() {
  const router = useRouter();
  const {
    currentMeeting,
    transcript,
    report,
    generating,
    selectMeeting,
    generateReport,
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
              <TabsList className="w-full justify-start bg-slate-100/80 dark:bg-slate-900/80 p-1 rounded-xl">
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
              </div>
            </Tabs>
          </div>
        </div>
      </div>
    </div>
  );
}
