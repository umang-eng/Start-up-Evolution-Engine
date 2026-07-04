'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useIntakeStore, IntakePhase } from '@/store/useIntakeStore';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Sparkles,
  Send,
  ArrowRight,
  Bot,
  User,
  CheckCircle,
  Loader2,
  MessageSquare,
  Lightbulb,
  RefreshCw,
} from 'lucide-react';

// ── Category Icons ─────────────────────────────────────────────────

const CATEGORY_ICONS: Record<string, string> = {
  manufacturing: '🏭',
  regulatory: '⚖️',
  market_validation: '📊',
  technical_feasibility: '🔧',
  competitive_landscape: '🏆',
  unit_economics: '💰',
  go_to_market: '🚀',
  team_composition: '👥',
  scalability: '📈',
  funding_strategy: '💎',
  customer_discovery: '🔍',
  risk_assessment: '⚠️',
  extraction: '🧬',
  system: '🤖',
};

// ── Main Component ─────────────────────────────────────────────────

interface IntakeChatProps {
  onComplete: (projectId: string) => void;
  onSkip: () => void;
}

export function IntakeChat({ onComplete, onSkip }: IntakeChatProps) {
  const {
    phase,
    error,
    extraction,
    currentQuestion,
    questionsRemaining,
    conversationLog,
    startSession,
    submitAnswer,
    finalizeSession,
    reset,
  } = useIntakeStore();

  const [inputVal, setInputVal] = useState('');
  const [answerVal, setAnswerVal] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationLog]);

  // Focus input when phase changes
  useEffect(() => {
    if (phase === 'idle') inputRef.current?.focus();
    if (phase === 'in_conversation') {
      setTimeout(() => {
        const el = document.getElementById('answer-input');
        el?.focus();
      }, 300);
    }
  }, [phase]);

  // Handle initial idea submission
  const handleStart = async () => {
    if (!inputVal.trim() || phase === 'analyzing') return;
    await startSession(inputVal.trim());
    setInputVal('');
    setAnswerVal('');
  };

  // Handle answer submission
  const handleAnswer = async () => {
    if (!answerVal.trim() || !currentQuestion || phase !== 'in_conversation') return;
    await submitAnswer(currentQuestion.question_id, answerVal.trim());
    setAnswerVal('');
  };

  // Handle finalization
  const handleFinalize = async () => {
    await finalizeSession();
  };

  // Detect when all questions are answered (no current question and phase is still in_conversation)
  const allQuestionsAnswered = phase === 'in_conversation' && !currentQuestion && questionsRemaining === 0;

  // Handle project creation after finalization
  useEffect(() => {
    if (phase === 'done') {
      // Small delay to show the "done" message
      const timer = setTimeout(() => {
        const projectId = useIntakeStore.getState().projectId;
        if (projectId) {
          onComplete(projectId);
        }
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [phase, onComplete]);

  return (
    <div className="flex flex-col h-full max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/60">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-accent-blue/10 flex items-center justify-center">
            <MessageSquare className="h-4 w-4 text-accent-blue" />
          </div>
          <div>
            <span className="text-sm font-semibold text-primary block">Startup Consultant</span>
            <span className="text-[10px] text-muted-foreground">AI-powered concept refinement</span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onSkip}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Skip to direct input
        </Button>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {/* Welcome Message */}
        {phase === 'idle' && conversationLog.length === 0 && (
          <div className="flex flex-col items-center text-center py-8 space-y-4">
            <div className="h-16 w-16 rounded-full bg-accent-blue/10 flex items-center justify-center">
              <Lightbulb className="h-8 w-8 text-accent-blue" />
            </div>
            <div className="space-y-2 max-w-md">
              <h3 className="text-lg font-bold text-primary">Refine Your Startup Concept</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Describe your startup idea below. Our AI consultant will analyze it, ask
                targeted follow-up questions based on your industry, and help you build a
                comprehensive concept brief before the pipeline runs.
              </p>
            </div>
          </div>
        )}

        {/* Conversation Log */}
        {conversationLog.map((msg, idx) => (
          <div
            key={idx}
            className={cn(
              'flex gap-3 max-w-[85%]',
              msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''
            )}
          >
            {/* Avatar */}
            <div
              className={cn(
                'h-7 w-7 rounded-full flex items-center justify-center shrink-0',
                msg.role === 'ai'
                  ? 'bg-accent-blue/10'
                  : 'bg-primary/10'
              )}
            >
              {msg.role === 'ai' ? (
                <Bot className="h-3.5 w-3.5 text-accent-blue" />
              ) : (
                <User className="h-3.5 w-3.5 text-primary" />
              )}
            </div>

            {/* Message Bubble */}
            <div
              className={cn(
                'rounded-xl px-4 py-3 text-sm leading-relaxed',
                msg.role === 'ai'
                  ? 'bg-white border border-border/60 shadow-lvl-1 text-foreground'
                  : 'bg-accent-blue text-white',
                msg.category === 'extraction' && 'border-accent-blue/30 bg-accent-blue/5',
                msg.category === 'system' && 'border-dashed bg-transparent text-muted-foreground italic text-xs',
              )}
            >
              {/* Category badge for questions */}
              {msg.category && msg.category !== 'system' && msg.category !== 'extraction' && (
                <span className="inline-block text-[10px] font-medium px-2 py-0.5 rounded-full bg-black/5 text-muted-foreground mb-2">
                  {CATEGORY_ICONS[msg.category] || '❓'} {msg.category.replace('_', ' ')}
                </span>
              )}

              {/* Message content with markdown-like rendering */}
              <div className="whitespace-pre-wrap">
                {msg.content.split('\n').map((line, i) => {
                  // Bold text
                  const parts = line.split(/(\*\*[^*]+\*\*)/g);
                  return (
                    <span key={i}>
                      {parts.map((part, j) => {
                        if (part.startsWith('**') && part.endsWith('**')) {
                          return <strong key={j}>{part.slice(2, -2)}</strong>;
                        }
                        return <span key={j}>{part}</span>;
                      })}
                      {i < msg.content.split('\n').length - 1 && <br />}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {phase === 'analyzing' && (
          <div className="flex gap-3">
            <div className="h-7 w-7 rounded-full bg-accent-blue/10 flex items-center justify-center shrink-0">
              <Bot className="h-3.5 w-3.5 text-accent-blue" />
            </div>
            <div className="rounded-xl px-4 py-3 bg-white border border-border/60 shadow-lvl-1">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin text-accent-blue" />
                <span>Analyzing your concept...</span>
              </div>
            </div>
          </div>
        )}

        {/* Finalizing indicator */}
        {phase === 'finalizing' && (
          <div className="flex gap-3">
            <div className="h-7 w-7 rounded-full bg-accent-blue/10 flex items-center justify-center shrink-0">
              <Bot className="h-3.5 w-3.5 text-accent-blue" />
            </div>
            <div className="rounded-xl px-4 py-3 bg-white border border-border/60 shadow-lvl-1">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin text-accent-blue" />
                <span>Compiling your concept brief...</span>
              </div>
            </div>
          </div>
        )}

        {/* Done indicator */}
        {phase === 'done' && (
          <div className="flex gap-3">
            <div className="h-7 w-7 rounded-full bg-green-100 flex items-center justify-center shrink-0">
              <CheckCircle className="h-3.5 w-3.5 text-green-600" />
            </div>
            <div className="rounded-xl px-4 py-3 bg-green-50 border border-green-200 text-sm text-green-700">
              Concept brief ready! Redirecting to workspace...
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Error Display */}
      {error && (
        <div className="px-4 py-2 bg-red-50 border-t border-red-200 text-xs text-red-600 flex items-center gap-2">
          <span>{error}</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={reset}
            className="h-6 text-[10px] text-red-600 hover:text-red-700"
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            Retry
          </Button>
        </div>
      )}

      {/* Input Area */}
      <div className="px-4 py-3 border-t border-border/60 bg-white/50 backdrop-blur-sm">
        {phase === 'idle' && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleStart();
            }}
            className="flex gap-2"
          >
            <Input
              ref={inputRef}
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder="Describe your startup idea..."
              className="flex-1 h-9"
            />
            <Button
              type="submit"
              disabled={!inputVal.trim()}
              className="h-9 px-4 gap-1.5"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>Analyze</span>
            </Button>
          </form>
        )}

        {phase === 'in_conversation' && currentQuestion && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAnswer();
            }}
            className="flex gap-2"
          >
            <Input
              id="answer-input"
              value={answerVal}
              onChange={(e) => setAnswerVal(e.target.value)}
              placeholder="Type your answer..."
              className="flex-1 h-9"
            />
            <Button
              type="submit"
              disabled={!answerVal.trim()}
              className="h-9 px-4 gap-1.5"
            >
              <Send className="h-3.5 w-3.5" />
              <span>Send</span>
            </Button>
          </form>
        )}

        {allQuestionsAnswered && (
          <div className="flex justify-center">
            <Button
              onClick={handleFinalize}
              className="h-9 px-6 gap-1.5 bg-accent-blue hover:bg-accent-blue/90"
            >
              <CheckCircle className="h-3.5 w-3.5" />
              <span>Finalize & Create Project</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}

        {/* Progress indicator */}
        {phase === 'in_conversation' && (
          <div className="flex items-center justify-center gap-2 mt-2">
            <span className="text-[10px] text-muted-foreground">
              Question {conversationLog.filter(m => m.role === 'user').length + 1} of{' '}
              {conversationLog.filter(m => m.role === 'user').length + questionsRemaining + 1}
            </span>
            <div className="flex gap-1">
              {Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className={cn(
                    'h-1 w-6 rounded-full transition-colors',
                    i < conversationLog.filter(m => m.role === 'user').length
                      ? 'bg-accent-blue'
                      : 'bg-black/10'
                  )}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
