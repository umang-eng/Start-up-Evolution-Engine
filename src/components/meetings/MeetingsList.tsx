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
} from 'lucide-react';
import { useMeetingStore, Meeting } from '@/store/use-meeting-store';

// ── Status Badge ──────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
    RECORDING: { color: 'bg-red-500/20 text-red-300', icon: <Mic className="h-3 w-3" />, label: 'Recording' },
    TRANSCRIBED: { color: 'bg-blue-500/20 text-blue-300', icon: <FileText className="h-3 w-3" />, label: 'Transcribed' },
    ANALYZED: { color: 'bg-green-500/20 text-green-300', icon: <CheckCircle className="h-3 w-3" />, label: 'Analyzed' },
    GENERATING: { color: 'bg-yellow-500/20 text-yellow-300', icon: <Loader2 className="h-3 w-3 animate-spin" />, label: 'Generating' },
    ERROR: { color: 'bg-red-500/20 text-red-300', icon: <Trash2 className="h-3 w-3" />, label: 'Error' },
  };
  const c = config[status] || config.RECORDING;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${c.color}`}>
      {c.icon}
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
  const created = new Date(meeting.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  const duration = meeting.duration_seconds
    ? `${Math.floor(meeting.duration_seconds / 60)}m ${meeting.duration_seconds % 60}s`
    : null;

  return (
    <Card
      className={`cursor-pointer transition-all hover:bg-white/10 ${
        selected ? 'bg-white/10 border-purple-500/50' : 'bg-white/5 border-white/10'
      }`}
      onClick={() => onSelect(meeting.id)}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-white font-medium truncate">
              {meeting.title || 'Untitled Meeting'}
            </h3>
            <div className="flex items-center gap-3 mt-1.5 text-xs text-white/50">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {created}
              </span>
              {duration && <span>{duration}</span>}
              {meeting.speaker_count && <span>{meeting.speaker_count} speakers</span>}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={meeting.status} />
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(meeting.id);
              }}
              className="h-8 w-8 p-0 text-white/40 hover:text-red-400 hover:bg-red-500/10"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
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

  if (loading && meetings.length === 0) {
    return (
      <Card className="bg-white/5 backdrop-blur-xl border-white/10">
        <CardContent className="p-12 text-center">
          <Loader2 className="h-8 w-8 text-white/40 mx-auto animate-spin" />
          <p className="text-white/40 mt-3">Loading meetings...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Your Meetings</h2>
        <Button
          onClick={fetchMeetings}
          variant="ghost"
          size="sm"
          className="text-white/50 hover:text-white"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-sm">
          {error}
        </div>
      )}

      {meetings.length === 0 ? (
        <Card className="bg-white/5 backdrop-blur-xl border-white/10">
          <CardContent className="p-12 text-center">
            <Mic className="h-12 w-12 text-white/20 mx-auto mb-3" />
            <p className="text-white/60">No meetings yet</p>
            <p className="text-white/40 text-sm mt-1">
              Record a meeting or upload a transcript to get started
            </p>
          </CardContent>
        </Card>
      ) : (
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
      )}
    </div>
  );
}
