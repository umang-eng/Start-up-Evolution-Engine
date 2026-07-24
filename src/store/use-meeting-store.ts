import { create } from 'zustand';
import { api } from '@/lib/api-client';

// ── Types ──────────────────────────────────────────────────────────

export type MeetingStatus = 'RECORDING' | 'TRANSCRIBED' | 'ANALYZED' | 'GENERATING' | 'ERROR';

export interface Meeting {
  id: string;
  user_id: string;
  project_id: string | null;
  title: string | null;
  status: MeetingStatus;
  duration_seconds: number | null;
  speaker_count: number | null;
  language: string | null;
  created_at: string;
}

export interface Transcript {
  id: string;
  meeting_id: string;
  raw_text: string;
  word_count: number | null;
  language_detected: string | null;
  created_at: string;
}

export interface ActionItem {
  task: string;
  owner: string | null;
  priority: string | null;
  deadline: string | null;
  status: string;
}

export interface MeetingReport {
  id: string;
  meeting_id: string;
  status: string;
  title: string | null;
  executive_summary: string | null;
  key_points: string[] | null;
  decisions: string[] | null;
  action_items: ActionItem[] | null;
  questions_raised: string[] | null;
  risks_concerns: string[] | null;
  agreements: string[] | null;
  disagreements: string[] | null;
  technical_topics: string[] | null;
  business_opportunities: string[] | null;
  follow_up_needed: string[] | null;
  overall_outcome: string | null;
  full_report_markdown: string | null;
  created_at: string;
  updated_at: string;
}

interface MeetingState {
  // Data
  meetings: Meeting[];
  currentMeeting: Meeting | null;
  transcript: Transcript | null;
  report: MeetingReport | null;

  // UI State
  loading: boolean;
  error: string | null;
  generating: boolean;

  // Actions
  fetchMeetings: () => Promise<void>;
  createMeeting: (title?: string, projectId?: string) => Promise<Meeting>;
  selectMeeting: (meetingId: string) => Promise<void>;
  deleteMeeting: (meetingId: string) => Promise<void>;
  uploadTranscript: (meetingId: string, rawText: string, language?: string) => Promise<void>;
  uploadAudio: (meetingId: string, audioBlob: Blob, filename?: string) => Promise<void>;
  generateReport: (meetingId: string) => Promise<MeetingReport>;
  clearCurrent: () => void;
}


// ── Store ──────────────────────────────────────────────────────────

export const useMeetingStore = create<MeetingState>((set, get) => ({
  meetings: [],
  currentMeeting: null,
  transcript: null,
  report: null,
  loading: false,
  error: null,
  generating: false,

  fetchMeetings: async () => {
    set({ loading: true, error: null });
    try {
      const data = await api.meetings.list();
      set({ meetings: Array.isArray(data) ? data : [], loading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to load meetings', loading: false });
    }
  },

  createMeeting: async (title?: string, projectId?: string) => {
    set({ loading: true, error: null });
    try {
      const meeting = await api.meetings.create({
        title,
        project_id: projectId,
        language: 'en',
      });
      set((state) => ({
        meetings: [meeting, ...state.meetings],
        currentMeeting: meeting,
        loading: false,
      }));
      return meeting;
    } catch (err: any) {
      set({ error: err.message || 'Failed to create meeting', loading: false });
      throw err;
    }
  },

  selectMeeting: async (meetingId: string) => {
    set({ loading: true, error: null });
    try {
      const [meeting, transcript, report] = await Promise.allSettled([
        api.meetings.get(meetingId),
        api.meetings.getTranscript(meetingId),
        api.meetings.getReport(meetingId),
      ]);
      set({
        currentMeeting: meeting.status === 'fulfilled' ? meeting.value : null,
        transcript: transcript.status === 'fulfilled' ? transcript.value : null,
        report: report.status === 'fulfilled' ? report.value : null,
        loading: false,
      });
    } catch (err: any) {
      set({ error: err.message || 'Failed to load meeting', loading: false });
    }
  },

  deleteMeeting: async (meetingId: string) => {
    try {
      await api.meetings.delete(meetingId);
      set((state) => ({
        meetings: state.meetings.filter((m) => m.id !== meetingId),
        currentMeeting: state.currentMeeting?.id === meetingId ? null : state.currentMeeting,
        transcript: state.currentMeeting?.id === meetingId ? null : state.transcript,
        report: state.currentMeeting?.id === meetingId ? null : state.report,
      }));
    } catch (err: any) {
      set({ error: err.message || 'Failed to delete meeting' });
    }
  },

  uploadTranscript: async (meetingId: string, rawText: string, language?: string) => {
    set({ loading: true, error: null });
    try {
      const transcript = await api.meetings.uploadTranscript(meetingId, rawText, language);
      set({ transcript, loading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to upload transcript', loading: false });
      throw err;
    }
  },

  uploadAudio: async (meetingId: string, audioBlob: Blob, filename?: string) => {
    set({ loading: true, error: null });
    try {
      const transcript = await api.meetings.uploadAudio(meetingId, audioBlob, filename);
      set({ transcript, loading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to transcribe audio', loading: false });
      throw err;
    }
  },

  generateReport: async (meetingId: string) => {
    set({ generating: true, error: null });
    try {
      const report = await api.meetings.generateReport(meetingId);
      set({ report, generating: false });
      // Update meeting status
      get().selectMeeting(meetingId);
      return report;
    } catch (err: any) {
      set({ error: err.message || 'Failed to generate report', generating: false });
      throw err;
    }
  },

  clearCurrent: () => {
    set({ currentMeeting: null, transcript: null, report: null });
  },
}));
