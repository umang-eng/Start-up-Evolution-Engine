'use client';

import React, { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Mic,
  Clock,
  Trash2,
  FileText,
  CheckCircle,
  Loader2,
  RefreshCw,
  Calendar,
  Users,
  Search,
} from 'lucide-react';
import { useMeetingStore, Meeting } from '@/store/use-meeting-store';

// ── Status Badge ──────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; dot: string; icon: React.ReactNode; label: string }> = {
    RECORDING: {
      bg: 'bg-red-50 dark:bg-red-950/30',
      text: 'text-red-600 dark:text-red-400',
      dot: 'bg-red-500',
      icon: <Mic className="h-3 w-3" />,
      label: 'Recording',
    },
    TRANSCRIBED: {
      bg: 'bg-blue-50 dark:bg-blue-950/30',
      text: 'text-blue-600 dark:text-blue-400',
      dot: 'bg-blue-500',
      icon: <FileText className="h-3 w-3" />,
      label: 'Transcribed',
    },
    ANALYZED: {
      bg: 'bg-emerald-50 dark:bg-emerald-950/30',
      text: 'text-emerald-600 dark:text-emerald-400',
      dot: 'bg-emerald-500',
      icon: <CheckCircle className="h-3 w-3" />,
      label: 'Analyzed',
    },
    GENERATING: {
      bg: 'bg-amber-50 dark:bg-amber-950/30',
      text: 'text-amber-600 dark:text-amber-400',
      dot: 'bg-amber-500',
      icon: <Loader2 className="h-3 w-3 animate-spin" />,
      label: 'Generating',
    },
    ERROR: {
      bg: 'bg-red-50 dark:bg-red-950/30',
      text: 'text-red-600 dark:text-red-400',
      dot: 'bg-red-500',
      icon: <Trash2 className="h-3 w-3" />,
      label: 'Error',
    },
  };
  const c = config[status] || config.RECORDING;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}


// ── Meeting Card ──────────────────────────────────────────────────

interface MeetingCardProps {
  meeting: Meeting;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  selected?: boolean;
}

function MeetingCard({ meeting, onSelect, onDelete, selected }: MeetingCardProps) {
  const created = new Date(meeting.created_at);
  const dateStr = created.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const timeStr = created.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

  const duration = meeting.duration_seconds
    ? `${Math.floor(meeting.duration_seconds / 60)}m ${meeting.duration_seconds % 60}s`
    : null;

  return (
    <div
      className={`group relative rounded-xl border p-4 cursor-pointer transition-all duration-200 ${
        selected
          ? 'bg-violet-50/80 dark:bg-violet-950/20 border-violet-300 dark:border-violet-800 shadow-sm'
          : 'bg-white dark:bg-slate-950 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:shadow-sm'
      }`}
      onClick={() => onSelect(meeting.id)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className={`font-medium truncate text-sm ${
            selected
              ? 'text-violet-900 dark:text-violet-100'
              : 'text-slate-900 dark:text-slate-100'
          }`}>
            {meeting.title || 'Untitled Meeting'}
          </h3>
          <div className="flex items-center gap-3 mt-2 text-xs text-slate-500 dark:text-slate-400">
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {dateStr}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {timeStr}
            </span>
            {duration && <span>{duration}</span>}
            {meeting.speaker_count && (
              <span className="flex items-center gap-1">
                <Users className="h-3 w-3" />
                {meeting.speaker_count}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status={meeting.status} />
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(meeting.id);
            }}
            className="opacity-0 group-hover:opacity-100 h-7 w-7 flex items-center justify-center rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-all"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}


// ── Meetings List ─────────────────────────────────────────────────

interface MeetingsListProps {
  onSelectMeeting?: (meetingId: string) => void;
}

export function MeetingsList({ onSelectMeeting }: MeetingsListProps) {
  const { meetings, loading, error, fetchMeetings, deleteMeeting, selectMeeting, currentMeeting } =
    useMeetingStore();

  useEffect(() => {
    fetchMeetings();
  }, [fetchMeetings]);

  const handleSelect = async (id: string) => {
    await selectMeeting(id);
    onSelectMeeting?.(id);
  };

  const handleDelete = async (id: string) => {
    if (confirm('Delete this meeting and all associated data?')) {
      await deleteMeeting(id);
    }
  };

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-wider">
          History
        </h2>
        <Button
          onClick={fetchMeetings}
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 text-red-600 dark:text-red-400 text-xs">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && meetings.length === 0 && (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-xl bg-slate-100 dark:bg-slate-900 animate-pulse" />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && meetings.length === 0 && (
        <Card className="border-dashed border-2 border-slate-200 dark:border-slate-800 bg-transparent">
          <CardContent className="p-8 text-center">
            <div className="flex items-center justify-center h-12 w-12 rounded-2xl bg-slate-100 dark:bg-slate-900 mx-auto mb-3">
              <Mic className="h-5 w-5 text-slate-300 dark:text-slate-600" />
            </div>
            <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">No meetings yet</p>
            <p className="text-slate-400 dark:text-slate-500 text-xs mt-1">
              Record or upload to get started
            </p>
          </CardContent>
        </Card>
      )}

      {/* Meeting List */}
      <div className="space-y-2">
        {meetings.map((meeting) => (
          <MeetingCard
            key={meeting.id}
            meeting={meeting}
            onSelect={handleSelect}
            onDelete={handleDelete}
            selected={currentMeeting?.id === meeting.id}
          />
        ))}
      </div>
    </div>
  );
}
