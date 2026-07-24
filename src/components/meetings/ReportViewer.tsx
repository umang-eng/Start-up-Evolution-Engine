'use client';

import React, { useState } from 'react';
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
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  Sparkles,
  Shield,
  TrendingUp,
  Lightbulb,
  GitBranch,
} from 'lucide-react';
import { useMeetingStore, MeetingReport } from '@/store/use-meeting-store';

// ── Collapsible Section ────────────────────────────────────────────

interface SectionProps {
  title: string;
  icon: React.ReactNode;
  items: string[] | null;
  color?: string;
  defaultOpen?: boolean;
}

function Section({ title, icon, items, color = 'text-slate-900 dark:text-white', defaultOpen = true }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  if (!items || items.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-slate-50/50 dark:bg-slate-900/50 hover:bg-slate-100/80 dark:hover:bg-slate-900/80 transition-colors"
      >
        <h3 className={`text-sm font-semibold ${color} flex items-center gap-2.5`}>
          {icon}
          {title}
          <span className="text-xs font-normal text-slate-400 dark:text-slate-500 ml-1">
            ({items.length})
          </span>
        </h3>
        {open ? (
          <ChevronDown className="h-4 w-4 text-slate-400" />
        ) : (
          <ChevronRight className="h-4 w-4 text-slate-400" />
        )}
      </button>
      {open && (
        <div className="px-5 py-3 bg-white dark:bg-slate-950">
          <ul className="space-y-2">
            {items.map((item, i) => (
              <li key={i} className="flex items-start gap-3 text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                <span className="mt-2 h-1.5 w-1.5 rounded-full bg-slate-300 dark:bg-slate-600 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}


// ── Action Items Table ────────────────────────────────────────────

function ActionItemsTable({ items }: { items: MeetingReport['action_items'] }) {
  const [open, setOpen] = useState(true);
  if (!items || items.length === 0) return null;

  const priorityConfig: Record<string, { bg: string; text: string; dot: string }> = {
    HIGH: { bg: 'bg-red-50 dark:bg-red-950/30', text: 'text-red-700 dark:text-red-400', dot: 'bg-red-500' },
    MEDIUM: { bg: 'bg-amber-50 dark:bg-amber-950/30', text: 'text-amber-700 dark:text-amber-400', dot: 'bg-amber-500' },
    LOW: { bg: 'bg-slate-50 dark:bg-slate-900', text: 'text-slate-600 dark:text-slate-400', dot: 'bg-slate-400' },
  };

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-slate-50/50 dark:bg-slate-900/50 hover:bg-slate-100/80 dark:hover:bg-slate-900/80 transition-colors"
      >
        <h3 className="text-sm font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-2.5">
          <Target className="h-4 w-4" />
          Action Items
          <span className="text-xs font-normal text-slate-400 dark:text-slate-500 ml-1">
            ({items.length})
          </span>
        </h3>
        {open ? (
          <ChevronDown className="h-4 w-4 text-slate-400" />
        ) : (
          <ChevronRight className="h-4 w-4 text-slate-400" />
        )}
      </button>
      {open && (
        <div className="bg-white dark:bg-slate-950">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-900">
                  <th className="text-left py-3 px-5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Task</th>
                  <th className="text-left py-3 px-5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Owner</th>
                  <th className="text-left py-3 px-5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Priority</th>
                  <th className="text-left py-3 px-5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Deadline</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, i) => {
                  const p = priorityConfig[item.priority || 'LOW'] || priorityConfig.LOW;
                  return (
                    <tr key={i} className="border-b border-slate-50 dark:border-slate-900/50 last:border-0 hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors">
                      <td className="py-3 px-5 text-slate-800 dark:text-slate-200 font-medium">{item.task}</td>
                      <td className="py-3 px-5">
                        {item.owner ? (
                          <span className="inline-flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
                            <span className="h-5 w-5 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-600 dark:text-slate-300">
                              {item.owner[0]}
                            </span>
                            {item.owner}
                          </span>
                        ) : (
                          <span className="text-slate-300 dark:text-slate-600">—</span>
                        )}
                      </td>
                      <td className="py-3 px-5">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${p.bg} ${p.text}`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${p.dot}`} />
                          {item.priority || 'LOW'}
                        </span>
                      </td>
                      <td className="py-3 px-5 text-slate-500 dark:text-slate-400">{item.deadline || '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}


// ── Copy to Clipboard Button ──────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button
      onClick={handleCopy}
      variant="ghost"
      size="sm"
      className="h-8 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
    >
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5 mr-1.5 text-green-500" />
          Copied
        </>
      ) : (
        <>
          <Copy className="h-3.5 w-3.5 mr-1.5" />
          Copy
        </>
      )}
    </Button>
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
    a.download = `${(report.title || 'meeting-report').replace(/[^a-zA-Z0-9]/g, '_')}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Empty state
  if (!report && !generating) {
    return (
      <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
        <CardContent className="p-16 text-center">
          <div className="flex items-center justify-center h-20 w-20 rounded-3xl bg-gradient-to-br from-violet-50 to-purple-50 dark:from-violet-950/30 dark:to-purple-950/30 mx-auto mb-6">
            <Sparkles className="h-9 w-9 text-violet-400 dark:text-violet-500" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
            Generate Intelligence Report
          </h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm mb-8 max-w-md mx-auto leading-relaxed">
            Upload a transcript first, then generate an AI-powered report with action items,
            key decisions, risks, and follow-ups.
          </p>
          {onGenerate && (
            <Button
              onClick={onGenerate}
              disabled={generating || !currentMeeting}
              className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white shadow-lg shadow-purple-500/25 px-6"
            >
              <Sparkles className="h-4 w-4 mr-2" />
              Generate Report
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  // Loading state
  if (generating) {
    return (
      <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
        <CardContent className="p-16 text-center">
          <div className="relative mx-auto w-20 h-20 mb-6">
            <div className="absolute inset-0 rounded-full bg-gradient-to-r from-violet-500 to-purple-500 animate-ping opacity-20" />
            <div className="relative h-20 w-20 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-xl shadow-purple-500/30">
              <Loader2 className="h-8 w-8 text-white animate-spin" />
            </div>
          </div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
            Analyzing Meeting
          </h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm max-w-sm mx-auto leading-relaxed">
            Extracting key insights, action items, and decisions from your transcript.
            This usually takes 20-40 seconds.
          </p>
          <div className="mt-6 flex items-center justify-center gap-2 text-xs text-slate-400 dark:text-slate-500">
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
            Processing with AI
          </div>
        </CardContent>
      </Card>
    );
  }

  const r = report!;

  return (
    <div className="space-y-4">
      {/* Report Header */}
      <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 overflow-hidden">
        <div className="h-1.5 bg-gradient-to-r from-violet-500 via-purple-500 to-fuchsia-500" />
        <CardHeader className="pb-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <CardTitle className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                <div className="flex items-center justify-center h-10 w-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-purple-500/20">
                  <FileText className="h-5 w-5 text-white" />
                </div>
                {r.title || 'Meeting Report'}
              </CardTitle>
              <p className="text-slate-500 dark:text-slate-400 text-sm mt-2 ml-[52px]">
                AI-generated intelligence report
              </p>
            </div>
            <div className="flex items-center gap-2">
              <CopyButton text={r.full_report_markdown || ''} />
              <Button
                onClick={handleDownloadMarkdown}
                variant="outline"
                size="sm"
                className="border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900"
              >
                <Download className="h-3.5 w-3.5 mr-1.5" />
                Export .md
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Executive Summary */}
      {r.executive_summary && (
        <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
          <CardContent className="p-6">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="h-7 w-7 rounded-lg bg-blue-50 dark:bg-blue-950/30 flex items-center justify-center">
                <Lightbulb className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                Executive Summary
              </h3>
            </div>
            <p className="text-slate-600 dark:text-slate-300 text-sm whitespace-pre-wrap leading-relaxed pl-[38px]">
              {r.executive_summary}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Sections Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Section
          title="Key Discussion Points"
          icon={<MessageSquare className="h-4 w-4 text-blue-500" />}
          items={r.key_points}
          color="text-blue-600 dark:text-blue-400"
          defaultOpen={true}
        />

        <Section
          title="Decisions Made"
          icon={<CheckCircle className="h-4 w-4 text-green-500" />}
          items={r.decisions}
          color="text-green-600 dark:text-green-400"
          defaultOpen={true}
        />

        <Section
          title="Questions Raised"
          icon={<MessageSquare className="h-4 w-4 text-amber-500" />}
          items={r.questions_raised}
          color="text-amber-600 dark:text-amber-400"
          defaultOpen={false}
        />

        <Section
          title="Risks & Concerns"
          icon={<Shield className="h-4 w-4 text-red-500" />}
          items={r.risks_concerns}
          color="text-red-600 dark:text-red-400"
          defaultOpen={false}
        />

        <Section
          title="Agreements"
          icon={<Users className="h-4 w-4 text-emerald-500" />}
          items={r.agreements}
          color="text-emerald-600 dark:text-emerald-400"
          defaultOpen={false}
        />

        <Section
          title="Disagreements"
          icon={<AlertTriangle className="h-4 w-4 text-orange-500" />}
          items={r.disagreements}
          color="text-orange-600 dark:text-orange-400"
          defaultOpen={false}
        />

        <Section
          title="Technical Topics"
          icon={<GitBranch className="h-4 w-4 text-cyan-500" />}
          items={r.technical_topics}
          color="text-cyan-600 dark:text-cyan-400"
          defaultOpen={false}
        />

        <Section
          title="Business Opportunities"
          icon={<TrendingUp className="h-4 w-4 text-purple-500" />}
          items={r.business_opportunities}
          color="text-purple-600 dark:text-purple-400"
          defaultOpen={false}
        />

        <div className="md:col-span-2">
          <Section
            title="Follow-up Needed"
            icon={<Clock className="h-4 w-4 text-amber-500" />}
            items={r.follow_up_needed}
            color="text-amber-600 dark:text-amber-400"
            defaultOpen={false}
          />
        </div>
      </div>

      {/* Action Items */}
      <ActionItemsTable items={r.action_items} />

      {/* Overall Outcome */}
      {r.overall_outcome && (
        <Card className="border-emerald-200 dark:border-emerald-900/50 bg-gradient-to-br from-emerald-50/50 to-green-50/30 dark:from-emerald-950/20 dark:to-green-950/10">
          <CardContent className="p-6">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="h-7 w-7 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                <CheckCircle className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              </div>
              <h3 className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
                Overall Outcome
              </h3>
            </div>
            <p className="text-slate-700 dark:text-slate-200 text-sm whitespace-pre-wrap leading-relaxed pl-[38px]">
              {r.overall_outcome}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
