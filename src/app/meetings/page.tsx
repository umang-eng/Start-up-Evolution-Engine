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
    // Switch to report tab if meeting has transcript
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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Button
            onClick={() => router.back()}
            variant="ghost"
            size="sm"
            className="text-white/50 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <Mic className="h-6 w-6 text-purple-400" />
              Conversation Intelligence
            </h1>
            <p className="text-white/50 text-sm mt-1">
              Record meetings, upload transcripts, and generate AI-powered intelligence reports
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Meeting List */}
          <div className="lg:col-span-1 space-y-4">
            <MeetingsList onSelectMeeting={handleSelectMeeting} />
          </div>

          {/* Right: Main Content */}
          <div className="lg:col-span-2">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="bg-white/5 border border-white/10">
                <TabsTrigger value="record" className="data-[state=active]:bg-purple-600">
                  <Mic className="h-4 w-4 mr-1" />
                  Record
                </TabsTrigger>
                <TabsTrigger value="upload" className="data-[state=active]:bg-blue-600">
                  <FileText className="h-4 w-4 mr-1" />
                  Upload
                </TabsTrigger>
                <TabsTrigger value="report" className="data-[state=active]:bg-green-600">
                  <BarChart3 className="h-4 w-4 mr-1" />
                  Report
                </TabsTrigger>
              </TabsList>

              <TabsContent value="record" className="mt-4">
                <AudioRecorder onComplete={handleRecordComplete} />
              </TabsContent>

              <TabsContent value="upload" className="mt-4">
                {selectedMeetingId ? (
                  <TranscriptUploader
                    meetingId={selectedMeetingId}
                    onComplete={() => selectMeeting(selectedMeetingId)}
                  />
                ) : (
                  <Card className="bg-white/5 backdrop-blur-xl border-white/10">
                    <CardContent className="p-12 text-center">
                      <FileText className="h-12 w-12 text-white/20 mx-auto mb-3" />
                      <p className="text-white/60">Select a meeting first</p>
                      <p className="text-white/40 text-sm mt-1">
                        Choose a meeting from the list to upload a transcript
                      </p>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="report" className="mt-4">
                <ReportViewer
                  onGenerate={handleGenerateReport}
                  generating={generating}
                />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </div>
  );
}
