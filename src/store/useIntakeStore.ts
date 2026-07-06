/**
 * Intake Store — Zustand state slice for the onboarding consultation chat.
 *
 * Manages the 3-phase intake flow:
 * 1. IDLE → user types raw idea
 * 2. IN_CONVERSATION → AI asks follow-ups, user answers one by one
 * 3. COMPLETE → all questions answered, ready to finalize
 * 4. FINALIZING → synthesis in progress
 * 5. DONE → project created, ready to navigate to workspace
 */

import { create } from 'zustand';
import { api } from '@/lib/api-client';

// ── Types ──────────────────────────────────────────────────────────

export type IntakePhase = 'idle' | 'analyzing' | 'in_conversation' | 'finalizing' | 'done';

export interface IntakeExtraction {
  industry: string;
  target_audience: string;
  core_value_proposition: string;
  detected_vertical_signals: string[];
}

export interface IntakeQuestion {
  question_id: string;
  question_text: string;
  category: string;
  rationale: string;
  priority: number;
}

export interface IntakeQA {
  question_id: string;
  question_text: string;
  category: string;
  answer: string;
}

export interface IntakeState {
  // Session
  phase: IntakePhase;
  sessionId: string | null;
  error: string | null;

  // Extraction results (from Phase 1)
  extraction: IntakeExtraction | null;

  // Conversation state
  currentQuestion: IntakeQuestion | null;
  questionsRemaining: number;
  conversationLog: Array<{
    role: 'ai' | 'user';
    content: string;
    category?: string;
    questionId?: string;
  }>;

  // Completed Q&A pairs
  answers: IntakeQA[];

  // Final result
  projectId: string | null;

  // Actions
  startSession: (rawIdea: string) => Promise<void>;
  submitAnswer: (questionId: string, answer: string) => Promise<void>;
  finalizeSession: () => Promise<void>;
  reset: () => void;
}


// ── Store ──────────────────────────────────────────────────────────

const initialState = {
  phase: 'idle' as IntakePhase,
  sessionId: null,
  error: null,
  extraction: null,
  currentQuestion: null,
  questionsRemaining: 0,
  conversationLog: [],
  answers: [],
  projectId: null,
};

export const useIntakeStore = create<IntakeState>()((set, get) => ({
  ...initialState,

  startSession: async (rawIdea: string) => {
    set({ phase: 'analyzing', error: null });

    try {
      const response = await api.intake.start(rawIdea);
      const data = response;

      set({
        phase: 'in_conversation',
        sessionId: data.session_id,
        extraction: data.extraction,
        currentQuestion: data.first_question,
        questionsRemaining: data.total_questions - 1,
        conversationLog: [
          {
            role: 'ai',
            content: `I've analyzed your idea. Here's what I detected:`,
            category: 'system',
          },
          {
            role: 'ai',
            content: `**Industry:** ${data.extraction.industry}\n**Target:** ${data.extraction.target_audience}\n**Value Prop:** ${data.extraction.core_value_proposition}`,
            category: 'extraction',
          },
          {
            role: 'ai',
            content: data.first_question.question_text,
            category: data.first_question.category,
            questionId: data.first_question.question_id,
          },
        ],
      });
    } catch (err: any) {
      set({
        phase: 'idle',
        error: err.message || 'Failed to analyze your idea. Please try again.',
      });
    }
  },

  submitAnswer: async (questionId: string, answer: string) => {
    const { sessionId, currentQuestion } = get();
    if (!sessionId || !currentQuestion) return;

    // Add user's answer to the log
    set((state) => ({
      conversationLog: [
        ...state.conversationLog,
        {
          role: 'user' as const,
          content: answer,
          category: currentQuestion.category,
          questionId,
        },
      ],
      answers: [
        ...state.answers,
        {
          question_id: questionId,
          question_text: currentQuestion.question_text,
          category: currentQuestion.category,
          answer,
        },
      ],
    }));

    try {
      const response = await api.intake.message(sessionId, questionId, answer);
      const data = response;

      if (data.is_complete) {
        // All questions answered
        set((state) => ({
          currentQuestion: null,
          questionsRemaining: 0,
          conversationLog: [
            ...state.conversationLog,
            {
              role: 'ai',
              content: 'All questions answered. Preparing your enriched concept brief...',
              category: 'system',
            },
          ],
        }));
      } else {
        // More questions remain
        set((state) => ({
          currentQuestion: data.next_question,
          questionsRemaining: data.questions_remaining,
          conversationLog: [
            ...state.conversationLog,
            {
              role: 'ai',
              content: data.next_question!.question_text,
              category: data.next_question!.category,
              questionId: data.next_question!.question_id,
            },
          ],
        }));
      }
    } catch (err: any) {
      set({
        error: err.message || 'Failed to submit answer. Please try again.',
      });
    }
  },

  finalizeSession: async () => {
    const { sessionId } = get();
    if (!sessionId) return;

    set({ phase: 'finalizing', error: null });

    try {
      const response = await api.intake.finalize(sessionId);
      const data = response;

      set((state) => ({
        phase: 'done',
        projectId: data.project_id,
        conversationLog: [
          ...state.conversationLog,
          {
            role: 'ai',
            content: 'Your concept brief has been compiled. Redirecting to workspace...',
            category: 'system',
          },
        ],
      }));
    } catch (err: any) {
      set({
        phase: 'in_conversation',
        error: err.message || 'Failed to finalize. Please try again.',
      });
    }
  },

  reset: () => set(initialState),
}));
