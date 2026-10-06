'use client';

import React, { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Upload, Loader2, FileText, CheckCircle, FileUp, AudioLines } from 'lucide-react';
import { useMeetingStore } from '@/store/use-meeting-store';

interface TranscriptUploaderProps {
  meetingId: string;
  onComplete?: () => void;
}

export function TranscriptUploader({ meetingId, onComplete }: TranscriptUploaderProps) {
  const { uploadTranscript, uploadAudio, loading } = useMeetingStore();
  const [text, setText] = useState('');
  const [uploaded, setUploaded] = useState<'text' | 'audio' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadType, setUploadType] = useState<'text' | 'audio' | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
  const transcriptExtensions = ['txt', 'md', 'srt', 'vtt'];
  const audioExtensions = ['mp3', 'm4a', 'wav', 'webm', 'ogg', 'flac', 'aac'];

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    const extension = file.name.split('.').pop()?.toLowerCase();
    if (audioExtensions.includes(extension || '')) {
      if (file.size > 100 * 1024 * 1024) {
        setError('Audio files must be 100 MB or smaller.');
        return;
      }
      setError(null);
      setText('');
      setUploaded(null);
      setUploadType('audio');
      try {
        await uploadAudio(meetingId, file, file.name);
        setUploaded('audio');
        onComplete?.();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to transcribe audio');
      } finally {
        setUploadType(null);
      }
      return;
    }

    if (!transcriptExtensions.includes(extension || '')) {
      setError('Choose a transcript (.txt, .md, .srt, .vtt) or audio (.mp3, .m4a, .wav, .webm, .ogg, .flac, .aac) file.');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError('Transcript files must be 5 MB or smaller.');
      return;
    }

    try {
      setText(await file.text());
      setUploaded(null);
      setError(null);
    } catch {
      setError('Could not read this file. Try another transcript file or paste the text instead.');
    }
  };

  const handleUpload = async () => {
    if (!text.trim()) return;
    setError(null);
    setUploadType('text');
    try {
      await uploadTranscript(meetingId, text);
      setUploaded('text');
      onComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload transcript');
    } finally {
      setUploadType(null);
    }
  };

  if (uploaded) {
    return (
      <Card className="border-border bg-card">
        <CardContent className="p-6 text-center">
          <CheckCircle className="h-12 w-12 text-green-600 dark:text-green-400 mx-auto mb-3" />
          <p className="text-foreground font-medium">
            {uploaded === 'audio' ? 'Audio Transcribed' : 'Transcript Uploaded'}
          </p>
          <p className="text-muted-foreground text-sm mt-1">
            {uploaded === 'text' ? `${wordCount} words saved. ` : 'Your audio was transcribed and saved. '}
            Go to the Report tab to generate analysis.
          </p>
          <Button className="mt-4" variant="outline" onClick={() => setUploaded(null)}>
            Replace transcript
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border bg-card">
      <CardHeader>
        <CardTitle className="text-foreground flex items-center gap-2 text-lg">
          <FileText className="h-5 w-5 text-primary" />
          Upload Transcript
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-700 dark:text-red-300 text-sm">
            {error}
          </div>
        )}

        <Textarea
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setUploaded(null);
          }}
          placeholder={`Paste your meeting transcript here...

Example format:
Speaker A: Let's discuss the Q3 roadmap.
Speaker B: I think we should prioritize the auth module.
Speaker A: Agreed. Can you own that by next Friday?`}
          className="min-h-[200px] resize-y border-border bg-background text-foreground placeholder:text-muted-foreground"
        />

        <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
          <span>{wordCount} words</span>
          <span>Transcript files up to 5 MB · Audio files up to 100 MB</span>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.srt,.vtt,.mp3,.m4a,.wav,.webm,.ogg,.flac,.aac,text/plain,text/markdown,audio/*"
          onChange={handleFileSelect}
          className="hidden"
          aria-label="Choose a transcript or audio file"
        />
        <Button
          type="button"
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          className="w-full"
        >
          {uploadType === 'audio' || (loading && uploadType !== 'text') ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <FileUp className="h-4 w-4 mr-2" />
          )}
          {uploadType === 'audio'
            ? 'Transcribing audio...'
            : loading
              ? 'Working...'
              : 'Choose transcript or audio file'}
        </Button>

        <Button
          onClick={handleUpload}
          disabled={loading || !text.trim()}
          className="w-full"
        >
          {uploadType === 'text' || loading ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Upload className="h-4 w-4 mr-2" />
          )}
          {uploadType === 'text' || loading ? 'Uploading transcript...' : 'Upload Transcript'}
        </Button>
        <p className="flex items-center justify-center gap-1.5 text-center text-xs text-muted-foreground">
          <AudioLines className="h-3.5 w-3.5" />
          Audio is transcribed automatically; audio formats include MP3, M4A, WAV, WebM, OGG, and FLAC.
        </p>
      </CardContent>
    </Card>
  );
}
