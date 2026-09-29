'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Upload, Loader2, FileText, CheckCircle } from 'lucide-react';
import { useMeetingStore } from '@/store/use-meeting-store';

interface TranscriptUploaderProps {
  meetingId: string;
  onComplete?: () => void;
}

export function TranscriptUploader({ meetingId, onComplete }: TranscriptUploaderProps) {
  const { uploadTranscript, loading } = useMeetingStore();
  const [text, setText] = useState('');
  const [uploaded, setUploaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wordCount = text.trim().split(/\s+/).filter(Boolean).length;

  const handleUpload = async () => {
    if (!text.trim()) return;
    setError(null);
    try {
      await uploadTranscript(meetingId, text);
      setUploaded(true);
      onComplete?.();
    } catch (err: any) {
      setError(err.message || 'Failed to upload transcript');
    }
  };

  if (uploaded) {
    return (
      <Card className="bg-white/5 backdrop-blur-xl border-white/10">
        <CardContent className="p-6 text-center">
          <CheckCircle className="h-12 w-12 text-green-400 mx-auto mb-3" />
          <p className="text-white font-medium">Transcript Uploaded</p>
          <p className="text-white/60 text-sm mt-1">
            {wordCount} words saved. Go to Report tab to generate analysis.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-white/5 backdrop-blur-xl border-white/10">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2 text-lg">
          <FileText className="h-5 w-5 text-blue-400" />
          Upload Transcript
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-sm">
            {error}
          </div>
        )}

        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste your meeting transcript here...

Example format:
Speaker A: Let's discuss the Q3 roadmap.
Speaker B: I think we should prioritize the auth module.
Speaker A: Agreed. Can you own that by next Friday?"
          className="min-h-[200px] bg-white/5 border-white/10 text-white placeholder:text-white/30 resize-y"
        />

        <div className="flex items-center justify-between text-sm text-white/50">
          <span>{wordCount} words</span>
          <span>Supports any text format</span>
        </div>

        <Button
          onClick={handleUpload}
          disabled={loading || !text.trim()}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Upload className="h-4 w-4 mr-2" />
          )}
          Upload Transcript
        </Button>
      </CardContent>
    </Card>
  );
}
