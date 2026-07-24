'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Mic,
  Square,
  Upload,
  Loader2,
  CheckCircle,
  Trash2,
  FileText,
  AlertCircle,
  Pause,
} from 'lucide-react';
import { useMeetingStore } from '@/store/use-meeting-store';

// ── MediaRecorder Hook ───────────────────────────────────────────

function useMediaRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    setIsSupported(typeof window !== 'undefined' && typeof MediaRecorder !== 'undefined');
  }, []);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });

      streamRef.current = stream;
      chunksRef.current = [];

      // Prefer webm Opus, fallback to whatever's available
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      const recorder = new MediaRecorder(stream, { mimeType });
      recorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        setAudioBlob(blob);
        // Stop all tracks
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.onerror = () => {
        setError('Recording failed. Try pasting your transcript instead.');
        setIsRecording(false);
      };

      recorder.start(1000); // Collect data every second
      recorderRef.current = recorder;
      setIsRecording(true);
      setIsPaused(false);
      setError(null);
      setElapsedTime(0);

      // Start timer
      timerRef.current = setInterval(() => {
        setElapsedTime((p) => p + 1);
      }, 1000);
    } catch (e: any) {
      if (e.name === 'NotAllowedError') {
        setError('Microphone access denied. Please allow mic access or paste your transcript.');
      } else {
        setError('Could not access microphone. Try pasting your transcript instead.');
      }
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
    }
    setIsRecording(false);
    setIsPaused(false);
  }, []);

  const pauseRecording = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state === 'recording') {
      recorderRef.current.pause();
      setIsPaused(true);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }, []);

  const resumeRecording = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state === 'paused') {
      recorderRef.current.resume();
      setIsPaused(false);
      timerRef.current = setInterval(() => {
        setElapsedTime((p) => p + 1);
      }, 1000);
    }
  }, []);

  const reset = useCallback(() => {
    setAudioBlob(null);
    setElapsedTime(0);
    setError(null);
    chunksRef.current = [];
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  return {
    isRecording,
    isPaused,
    elapsedTime,
    audioBlob,
    error,
    isSupported,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    reset,
  };
}


// ── Main Component ────────────────────────────────────────────────

interface AudioRecorderProps {
  onComplete?: (meetingId: string) => void;
}

export function AudioRecorder({ onComplete }: AudioRecorderProps) {
  const { createMeeting, uploadAudio, uploadTranscript, loading } = useMeetingStore();
  const {
    isRecording,
    isPaused,
    elapsedTime,
    audioBlob,
    error: recorderError,
    isSupported,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    reset: resetRecorder,
  } = useMediaRecorder();

  const [title, setTitle] = useState('');
  const [meetingId, setMeetingId] = useState<string | null>(null);
  const [pasteText, setPasteText] = useState('');
  const [transcribing, setTranscribing] = useState(false);
  const [step, setStep] = useState<'setup' | 'recording' | 'review' | 'done'>('setup');

  const formatTime = (s: number) =>
    `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;

  // Start live recording
  const handleStartRecording = async () => {
    try {
      const meeting = await createMeeting(title || undefined);
      setMeetingId(meeting.id);
      setStep('recording');
      await startRecording();
    } catch {}
  };

  // Stop recording → review
  const handleStop = () => {
    stopRecording();
    setStep('review');
  };

  // Upload audio for transcription
  const handleTranscribe = async () => {
    if (!meetingId || !audioBlob) return;
    setTranscribing(true);
    try {
      await uploadAudio(meetingId, audioBlob, 'recording.webm');
      setStep('done');
      onComplete?.(meetingId);
    } catch {
      setTranscribing(false);
    }
  };

  // Paste text directly
  const handlePasteSubmit = async () => {
    if (!pasteText.trim()) return;
    try {
      const meeting = await createMeeting(title || undefined);
      setMeetingId(meeting.id);
      await uploadTranscript(meeting.id, pasteText);
      setStep('done');
      onComplete?.(meeting.id);
    } catch {}
  };

  const handleReset = () => {
    resetRecorder();
    setMeetingId(null);
    setTitle('');
    setPasteText('');
    setStep('setup');
    setTranscribing(false);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Card className="w-full max-w-2xl mx-auto bg-white/5 backdrop-blur-xl border-white/10">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <Mic className="h-5 w-5 text-purple-400" />
          Conversation Intelligence
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {recorderError && (
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-sm flex items-start gap-2">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            {recorderError}
          </div>
        )}

        {/* ── Setup ── */}
        {step === 'setup' && (
          <div className="space-y-4">
            <div>
              <label className="text-sm text-white/60 mb-1.5 block">Meeting Title (optional)</label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Weekly Standup, Client Call..."
                className="bg-white/5 border-white/10 text-white placeholder:text-white/30"
              />
            </div>

            {/* Paste transcript */}
            <div>
              <label className="text-sm text-white/60 mb-1.5 block flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5" />
                Paste Transcript
              </label>
              <Textarea
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                placeholder={"Speaker A: Let's discuss the roadmap.\nSpeaker B: I think we should prioritize auth.\nSpeaker A: Agreed. Own it by Friday?"}
                className="min-h-[120px] bg-white/5 border-white/10 text-white placeholder:text-white/30 resize-y font-mono text-sm"
              />
            </div>

            <div className="flex gap-3">
              {isSupported && (
                <Button
                  onClick={handleStartRecording}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white"
                >
                  <Mic className="h-4 w-4 mr-2" />
                  Record Audio
                </Button>
              )}
              <Button
                onClick={handlePasteSubmit}
                disabled={!pasteText.trim() || loading}
                className={`flex-1 bg-purple-600 hover:bg-purple-700 text-white ${!isSupported ? 'w-full' : ''}`}
              >
                {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
                Use Pasted Text
              </Button>
            </div>

            {!isSupported && (
              <p className="text-xs text-white/30 text-center">
                Audio recording requires a modern browser with MediaRecorder support
              </p>
            )}
          </div>
        )}

        {/* ── Recording ── */}
        {step === 'recording' && (
          <div className="space-y-4">
            <div className="p-6 rounded-2xl bg-red-500/10 border border-red-500/20 text-center">
              <div className="relative mx-auto w-20 h-20">
                {!isPaused && <div className="absolute inset-0 rounded-full bg-red-500/20 animate-ping" />}
                <div className={`relative h-20 w-20 rounded-full flex items-center justify-center ${isPaused ? 'bg-yellow-500/30' : 'bg-red-500/30'}`}>
                  {isPaused ? <Pause className="h-8 w-8 text-yellow-400" /> : <Mic className="h-8 w-8 text-red-400" />}
                </div>
              </div>
              <p className={`mt-3 font-mono text-3xl font-bold ${isPaused ? 'text-yellow-300' : 'text-red-300'}`}>
                {formatTime(elapsedTime)}
              </p>
              <p className="text-white/50 text-xs mt-1">
                {isPaused ? 'Paused — click Resume to continue' : 'Recording in progress...'}
              </p>
            </div>

            <div className="flex gap-3">
              {isPaused ? (
                <Button onClick={resumeRecording} variant="outline" className="flex-1 border-white/10 text-white hover:bg-white/5">
                  Resume
                </Button>
              ) : (
                <Button onClick={pauseRecording} variant="outline" className="flex-1 border-white/10 text-white hover:bg-white/5">
                  <Pause className="h-4 w-4 mr-2" />
                  Pause
                </Button>
              )}
              <Button onClick={handleStop} variant="destructive" className="flex-1">
                <Square className="h-4 w-4 mr-2" />
                Stop & Transcribe
              </Button>
            </div>
          </div>
        )}

        {/* ── Review ── */}
        {step === 'review' && (
          <div className="space-y-4">
            {audioBlob && (
              <div className="p-4 rounded-lg bg-white/5 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-white/80 font-medium">Recorded Audio</span>
                  <span className="text-white/40">{formatSize(audioBlob.size)} &middot; {formatTime(elapsedTime)}</span>
                </div>
                <audio controls src={URL.createObjectURL(audioBlob)} className="w-full h-10" />
              </div>
            )}

            <div className="flex gap-3">
              <Button
                onClick={handleReset}
                variant="outline"
                className="flex-1 border-white/10 text-white hover:bg-white/5"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Discard
              </Button>
              <Button
                onClick={handleTranscribe}
                disabled={transcribing || loading || !audioBlob}
                className="flex-1 bg-purple-600 hover:bg-purple-700 text-white"
              >
                {transcribing || loading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4 mr-2" />
                )}
                {transcribing ? 'Transcribing...' : 'Send to Whisper'}
              </Button>
            </div>
          </div>
        )}

        {/* ── Done ── */}
        {step === 'done' && (
          <div className="text-center space-y-4 py-4">
            <CheckCircle className="h-14 w-14 text-green-400 mx-auto" />
            <p className="text-white text-lg font-medium">Transcript Ready</p>
            <p className="text-white/50 text-sm max-w-sm mx-auto">
              Switch to the <strong>Report</strong> tab to generate your AI intelligence report.
            </p>
            <Button onClick={handleReset} variant="outline" className="border-white/10 text-white hover:bg-white/5">
              Record Another
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
