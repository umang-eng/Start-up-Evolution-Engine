'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  FileText,
  CheckCircle,
  AlertTriangle,
  MessageSquare,
  Users,
  Target,
  Clock,
  Download,
  Loader2,
} from 'lucide-react';
import { useMeetingStore, MeetingReport } from '@/store/use-meeting-store';

// ── Section Component ─────────────────────────────────────────────

interface SectionProps {
  title: string;
  icon: React.ReactNode;
  items: string[] | null;
  color?: string;
}

function Section({ title, icon, items, color = 'text-white' }: SectionProps) {
  if (!items || items.length === 0) return null;
  return (
    <div className="space-y-2">
      <h3 className={`text-sm font-semibold ${color} flex items-center gap-2`}>
        {icon}
        {title}
      </h3>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="text-white/70 text-sm pl-6 relative">
            <span className="absolute left-2 top-2 h-1.5 w-1.5 rounded-full bg-white/30" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}


// ── Action Items Table ────────────────────────────────────────────

function ActionItemsTable({ items }: { items: MeetingReport['action_items'] }) {
  if (!items || items.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-yellow-400 flex items-center gap-2">
        <Target className="h-4 w-4" />
        Action Items ({items.length})
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left py-2 px-3 text-white/50 font-medium">Task</th>
              <th className="text-left py-2 px-3 text-white/50 font-medium">Owner</th>
              <th className="text-left py-2 px-3 text-white/50 font-medium">Priority</th>
              <th className="text-left py-2 px-3 text-white/50 font-medium">Deadline</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr key={i} className="border-b border-white/5">
                <td className="py-2 px-3 text-white/80">{item.task}</td>
                <td className="py-2 px-3 text-white/60">{item.owner || '-'}</td>
                <td className="py-2 px-3">
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    item.priority === 'HIGH' ? 'bg-red-500/20 text-red-300' :
                    item.priority === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-300' :
                    'bg-white/10 text-white/60'
                  }`}>
                    {item.priority || 'LOW'}
                  </span>
                </td>
                <td className="py-2 px-3 text-white/60">{item.deadline || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


// ── Main Report Viewer ────────────────────────────────────────────

interface ReportViewerProps {
  onGenerate?: () => void;
  generating?: boolean;
}

export function ReportViewer({ onGenerate, generating }: ReportViewerProps) {
  const { report, currentMeeting } = useMeetingStore();

  const handleDownloadMarkdown = () => {
    if (!report?.full_report_markdown) return;
    const blob = new Blob([report.full_report_markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.title || 'meeting-report'}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // No report yet
  if (!report && !generating) {
    return (
      <Card className="bg-white/5 backdrop-blur-xl border-white/10">
        <CardContent className="p-12 text-center">
          <FileText className="h-16 w-16 text-white/20 mx-auto mb-4" />
          <p className="text-white/60 text-lg mb-2">No Report Yet</p>
          <p className="text-white/40 text-sm mb-6">
            Upload a transcript first, then generate an AI-powered intelligence report.
          </p>
          {onGenerate && (
            <Button
              onClick={onGenerate}
              disabled={generating}
              className="bg-purple-600 hover:bg-purple-700 text-white"
            >
              {generating ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <FileText className="h-4 w-4 mr-2" />
              )}
              Generate Report
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  // Generating state
  if (generating) {
    return (
      <Card className="bg-white/5 backdrop-blur-xl border-white/10">
        <CardContent className="p-12 text-center">
          <Loader2 className="h-16 w-16 text-purple-400 mx-auto mb-4 animate-spin" />
          <p className="text-white text-lg font-medium mb-2">Generating Report...</p>
          <p className="text-white/40 text-sm">
            Analyzing transcript and extracting intelligence. This may take 30-60 seconds.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Report ready
  const r = report!;

  return (
    <Card className="bg-white/5 backdrop-blur-xl border-white/10">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-white flex items-center gap-2">
            <FileText className="h-5 w-5 text-green-400" />
            {r.title || 'Meeting Report'}
          </CardTitle>
          <Button
            onClick={handleDownloadMarkdown}
            variant="outline"
            size="sm"
            className="border-white/10 text-white hover:bg-white/5"
          >
            <Download className="h-4 w-4 mr-1" />
            Export .md
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Executive Summary */}
        {r.executive_summary && (
          <div className="p-4 rounded-lg bg-white/5 border border-white/10">
            <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
              <FileText className="h-4 w-4 text-blue-400" />
              Executive Summary
            </h3>
            <p className="text-white/70 text-sm whitespace-pre-wrap leading-relaxed">
              {r.executive_summary}
            </p>
          </div>
        )}

        {/* Key Points */}
        <Section
          title="Key Discussion Points"
          icon={<MessageSquare className="h-4 w-4 text-blue-400" />}
          items={r.key_points}
          color="text-blue-400"
        />

        {/* Decisions */}
        <Section
          title="Decisions Made"
          icon={<CheckCircle className="h-4 w-4 text-green-400" />}
          items={r.decisions}
          color="text-green-400"
        />

        {/* Action Items */}
        <ActionItemsTable items={r.action_items} />

        {/* Questions */}
        <Section
          title="Questions Raised"
          icon={<MessageSquare className="h-4 w-4 text-yellow-400" />}
          items={r.questions_raised}
          color="text-yellow-400"
        />

        {/* Risks */}
        <Section
          title="Risks / Concerns"
          icon={<AlertTriangle className="h-4 w-4 text-red-400" />}
          items={r.risks_concerns}
          color="text-red-400"
        />

        {/* Agreements */}
        <Section
          title="Agreements"
          icon={<Users className="h-4 w-4 text-emerald-400" />}
          items={r.agreements}
          color="text-emerald-400"
        />

        {/* Disagreements */}
        <Section
          title="Disagreements"
          icon={<AlertTriangle className="h-4 w-4 text-orange-400" />}
          items={r.disagreements}
          color="text-orange-400"
        />

        {/* Technical Topics */}
        <Section
          title="Technical Topics"
          icon={<FileText className="h-4 w-4 text-cyan-400" />}
          items={r.technical_topics}
          color="text-cyan-400"
        />

        {/* Business Opportunities */}
        <Section
          title="Business Opportunities"
          icon={<Target className="h-4 w-4 text-purple-400" />}
          items={r.business_opportunities}
          color="text-purple-400"
        />

        {/* Follow-up */}
        <Section
          title="Follow-up Needed"
          icon={<Clock className="h-4 w-4 text-amber-400" />}
          items={r.follow_up_needed}
          color="text-amber-400"
        />

        {/* Overall Outcome */}
        {r.overall_outcome && (
          <div className="p-4 rounded-lg bg-green-500/5 border border-green-500/20">
            <h3 className="text-sm font-semibold text-green-400 mb-2 flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              Overall Outcome
            </h3>
            <p className="text-white/70 text-sm whitespace-pre-wrap leading-relaxed">
              {r.overall_outcome}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
