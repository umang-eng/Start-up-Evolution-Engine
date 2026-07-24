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
  Play,
  RotateCcw,
  AudioLines,
  Sparkles,
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
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.onerror = () => {
        setError('Recording failed. Try pasting your transcript instead.');
        setIsRecording(false);
      };

      recorder.start(1000);
      recorderRef.current = recorder;
      setIsRecording(true);
      setIsPaused(false);
      setError(null);
      setElapsedTime(0);

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


// ── Waveform Visualizer ──────────────────────────────────────────

function WaveformVisualizer({ isPaused }: { isPaused: boolean }) {
  return (
    <div className="flex items-center justify-center gap-1 h-12">
      {Array.from({ length: 24 }).map((_, i) => (
        <div
          key={i}
          className={`w-1 rounded-full transition-all duration-150 ${
            isPaused
              ? 'h-1 bg-slate-300 dark:bg-slate-600'
              : 'bg-gradient-to-t from-violet-500 to-purple-400 animate-pulse'
          }`}
          style={{
            height: isPaused ? undefined : `${Math.random() * 32 + 8}px`,
            animationDelay: `${i * 0.05}s`,
            animationDuration: `${0.3 + Math.random() * 0.4}s`,
          }}
        />
      ))}
    </div>
  );
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

  const handleStartRecording = async () => {
    try {
      const meeting = await createMeeting(title || undefined);
      setMeetingId(meeting.id);
      setStep('recording');
      await startRecording();
    } catch {}
  };

  const handleStop = () => {
    stopRecording();
    setStep('review');
  };

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
    <Card className="w-full border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
      <CardHeader className="pb-4">
        <CardTitle className="text-slate-900 dark:text-white flex items-center gap-2.5">
          <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-gradient-to-br from-red-500 to-rose-600 shadow-lg shadow-red-500/25">
            <Mic className="h-4 w-4 text-white" />
          </div>
          New Recording
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Error */}
        {recorderError && (
          <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 text-amber-700 dark:text-amber-400 text-sm flex items-start gap-2.5">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            {recorderError}
          </div>
        )}

        {/* Setup Step */}
        {step === 'setup' && (
          <div className="space-y-5">
            <div>
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2 block uppercase tracking-wider">
                Meeting Title
              </label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Weekly Standup, Client Call..."
                className="h-10 bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2 block uppercase tracking-wider">
                Or Paste Transcript
              </label>
              <Textarea
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                placeholder={"Speaker A: Let's discuss the roadmap.\nSpeaker B: I think we should prioritize auth.\nSpeaker A: Agreed. Own it by Friday?"}
                className="min-h-[140px] bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 resize-y font-mono text-sm"
              />
              {pasteText.trim() && (
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-1.5">
                  {pasteText.trim().split(/\s+/).filter(Boolean).length} words
                </p>
              )}
            </div>

            <div className="flex gap-3">
              {isSupported && (
                <Button
                  onClick={handleStartRecording}
                  className="flex-1 bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-600 hover:to-rose-700 text-white shadow-lg shadow-red-500/25 h-11"
                >
                  <Mic className="h-4 w-4 mr-2" />
                  Record Audio
                </Button>
              )}
              <Button
                onClick={handlePasteSubmit}
                disabled={!pasteText.trim() || loading}
                className={`flex-1 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white shadow-lg shadow-purple-500/25 h-11 ${
                  !isSupported ? 'w-full' : ''
                }`}
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4 mr-2" />
                )}
                {loading ? 'Processing...' : 'Use Pasted Text'}
              </Button>
            </div>

            {!isSupported && (
              <p className="text-xs text-slate-400 dark:text-slate-500 text-center">
                Audio recording requires a modern browser with MediaRecorder support
              </p>
            )}
          </div>
        )}

        {/* Recording Step */}
        {step === 'recording' && (
          <div className="space-y-5">
            <div className="py-8 rounded-2xl bg-gradient-to-br from-red-50 to-rose-50 dark:from-red-950/20 dark:to-rose-950/20 border border-red-200/50 dark:border-red-900/30 text-center">
              <div className="relative mx-auto w-20 h-20 mb-4">
                {!isPaused && (
                  <>
                    <div className="absolute inset-0 rounded-full bg-red-400/20 animate-ping" />
                    <div className="absolute inset-1 rounded-full bg-red-400/10 animate-ping" style={{ animationDelay: '0.5s' }} />
                  </>
                )}
                <div className={`relative h-20 w-20 rounded-full flex items-center justify-center shadow-xl ${
                  isPaused
                    ? 'bg-gradient-to-br from-amber-400 to-orange-500 shadow-amber-500/30'
                    : 'bg-gradient-to-br from-red-500 to-rose-600 shadow-red-500/30'
                }`}>
                  {isPaused ? (
                    <Pause className="h-8 w-8 text-white" />
                  ) : (
                    <AudioLines className="h-8 w-8 text-white" />
                  )}
                </div>
              </div>

              <p className={`font-mono text-4xl font-bold tracking-tight ${
                isPaused ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'
              }`}>
                {formatTime(elapsedTime)}
              </p>
              <p className="text-slate-500 dark:text-slate-400 text-sm mt-2">
                {isPaused ? 'Recording paused' : 'Recording in progress...'}
              </p>

              {!isPaused && <WaveformVisualizer isPaused={isPaused} />}
            </div>

            <div className="flex gap-3">
              {isPaused ? (
                <Button
                  onClick={resumeRecording}
                  variant="outline"
                  className="flex-1 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900 h-11"
                >
                  <Play className="h-4 w-4 mr-2" />
                  Resume
                </Button>
              ) : (
                <Button
                  onClick={pauseRecording}
                  variant="outline"
                  className="flex-1 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900 h-11"
                >
                  <Pause className="h-4 w-4 mr-2" />
                  Pause
                </Button>
              )}
              <Button
                onClick={handleStop}
                className="flex-1 bg-gradient-to-r from-slate-800 to-slate-900 hover:from-slate-700 hover:to-slate-800 text-white shadow-lg h-11"
              >
                <Square className="h-4 w-4 mr-2" />
                Stop & Transcribe
              </Button>
            </div>
          </div>
        )}

        {/* Review Step */}
        {step === 'review' && (
          <div className="space-y-5">
            {audioBlob && (
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                <div className="flex items-center justify-between text-sm mb-3">
                  <span className="text-slate-900 dark:text-white font-medium flex items-center gap-2">
                    <AudioLines className="h-4 w-4 text-violet-500" />
                    Recorded Audio
                  </span>
                  <span className="text-slate-500 dark:text-slate-400 text-xs">
                    {formatSize(audioBlob.size)} · {formatTime(elapsedTime)}
                  </span>
                </div>
                <audio
                  controls
                  src={URL.createObjectURL(audioBlob)}
                  className="w-full h-10 [&::-webkit-media-controls-panel]:bg-slate-100 dark:[&::-webkit-media-controls-panel]:bg-slate-800"
                />
              </div>
            )}

            <div className="flex gap-3">
              <Button
                onClick={handleReset}
                variant="outline"
                className="flex-1 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900 h-11"
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Discard
              </Button>
              <Button
                onClick={handleTranscribe}
                disabled={transcribing || loading || !audioBlob}
                className="flex-1 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white shadow-lg shadow-purple-500/25 h-11"
              >
                {transcribing || loading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4 mr-2" />
                )}
                {transcribing ? 'Transcribing...' : 'Transcribe with AI'}
              </Button>
            </div>
          </div>
        )}

        {/* Done Step */}
        {step === 'done' && (
          <div className="text-center space-y-5 py-6">
            <div className="relative mx-auto w-16 h-16">
              <div className="absolute inset-0 rounded-full bg-emerald-400/20 animate-ping" />
              <div className="relative h-16 w-16 rounded-full bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center shadow-xl shadow-emerald-500/30">
                <CheckCircle className="h-7 w-7 text-white" />
              </div>
            </div>
            <div>
              <p className="text-slate-900 dark:text-white text-lg font-semibold">Transcript Ready</p>
              <p className="text-slate-500 dark:text-slate-400 text-sm mt-1.5 max-w-sm mx-auto">
                Switch to the <strong>Report</strong> tab to generate your AI intelligence report.
              </p>
            </div>
            <Button
              onClick={handleReset}
              variant="outline"
              className="border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900"
            >
              <Mic className="h-4 w-4 mr-2" />
              Record Another
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
