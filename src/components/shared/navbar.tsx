'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useBlueprintStore } from '@/store/use-blueprint-store';
import { useAuth } from '@/components/shared/auth-provider';
import { api } from '@/lib/api-client';
import { StageName } from '@/types/blueprint';
import { 
  Search, 
  Bell, 
  Share2, 
  Download, 
  ChevronDown,
  LogOut,
  User,
  Check,
  Cpu,
  Clock,
  DollarSign,
  TrendingUp,
  Settings,
  Folder,
  Command
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SettingsDialog } from './settings-dialog';
import { useSettingsStore } from '@/store/use-settings-store';
import { Badge } from '@/components/ui/badge';

export function Navbar() {
  const { projects, activeProjectId, setActiveStage, setActiveProject } = useBlueprintStore();
  const { user, logout } = useAuth();
  
  const activeProject = projects.find(p => p.id === activeProjectId);

  const [profileOpen, setProfileOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settings = useSettingsStore();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  const [shareStatus, setShareStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [exportStatus, setExportStatus] = useState<'idle' | 'loading'>('idle');

  const profileRef = useRef<HTMLDivElement>(null);
  const notificationsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setProfileOpen(false);
      }
      if (notificationsRef.current && !notificationsRef.current.contains(event.target as Node)) {
        setNotificationsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(prev => !prev);
      }
      if (e.key === 'Escape') {
        setSearchOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleShare = async () => {
    if (!activeProject) return;
    setShareStatus('loading');
    try {
      const payload = await api.exports.share(activeProject.id);
      const url = `${window.location.origin}/shared/${payload.token}`;
      await navigator.clipboard.writeText(url);
      setShareStatus('success');
      setTimeout(() => setShareStatus('idle'), 2500);
    } catch (err) {
      console.error('Failed to share project:', err);
      setShareStatus('error');
      setTimeout(() => setShareStatus('idle'), 2500);
    }
  };

  const handleExport = () => {
    if (!activeProject) return;
    setExportStatus('loading');
    window.open(api.exports.pdf(activeProject.id), '_blank');
    setTimeout(() => setExportStatus('idle'), 1500);
  };

  const getSearchResults = () => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase();
    const results: Array<{
      id: string;
      projectId: string;
      title: string;
      subtitle: string;
      stage: StageName;
      type: 'project' | 'dna' | 'feature' | 'task' | 'role' | 'cost';
    }> = [];

    projects.forEach((proj) => {
      if (proj.name.toLowerCase().includes(q)) {
        results.push({
          id: `${proj.id}-project`,
          projectId: proj.id,
          title: proj.name,
          subtitle: proj.ideaPrompt || 'No description',
          stage: 'dna-analyzer',
          type: 'project',
        });
      }
      if (proj.dna) {
        if (proj.dna.category.toLowerCase().includes(q) || proj.dna.usp.toLowerCase().includes(q)) {
          results.push({
            id: `${proj.id}-dna`,
            projectId: proj.id,
            title: proj.name,
            subtitle: `DNA: ${proj.dna.usp}`,
            stage: 'dna-analyzer',
            type: 'dna',
          });
        }
      }
      if (proj.features?.features) {
        proj.features.features.forEach((f) => {
          if (f.name.toLowerCase().includes(q) || f.description.toLowerCase().includes(q)) {
            results.push({
              id: `${proj.id}-feat-${f.id}`,
              projectId: proj.id,
              title: `${proj.name} › ${f.name}`,
              subtitle: f.description,
              stage: 'feature-extractor',
              type: 'feature',
            });
          }
        });
      }
      if (proj.roadmap?.phases) {
        proj.roadmap.phases.forEach((phase) => {
          phase.tasks.forEach((t) => {
            if (t.name.toLowerCase().includes(q)) {
              results.push({
                id: `${proj.id}-task-${t.id}`,
                projectId: proj.id,
                title: `${proj.name} › ${t.name}`,
                subtitle: `Phase: ${phase.name}`,
                stage: 'roadmap',
                type: 'task',
              });
            }
          });
        });
      }
    });

    return results.slice(0, 8);
  };

  const searchResults = getSearchResults();

  const getNotifications = () => {
    if (!activeProject) return [];
    const logs: Array<{ id: string; text: string; time: string; stage: StageName }> = [];
    if (activeProject.dna) {
      logs.push({ id: 'n1', text: 'Venture DNA structured', time: 'Stage 1', stage: 'dna-analyzer' });
    }
    if (activeProject.features) {
      logs.push({ id: 'n2', text: 'Features spec compiled', time: 'Stage 2', stage: 'feature-extractor' });
    }
    if (activeProject.roadmap) {
      logs.push({ id: 'n3', text: 'Roadmap created', time: 'Stage 3', stage: 'roadmap' });
    }
    if (activeProject.team) {
      logs.push({ id: 'n4', text: 'Team structure defined', time: 'Stage 4', stage: 'team-structure' });
    }
    if (activeProject.swot) {
      logs.push({ id: 'n5', text: 'SWOT analysis complete', time: 'Stage 5', stage: 'swot' });
    }
    if (activeProject.cost) {
      logs.push({ id: 'n6', text: 'Cost estimation done', time: 'Stage 6', stage: 'cost-estimator' });
    }
    return logs.reverse();
  };

  const notifications = getNotifications();

  return (
    <>
      <header className="h-14 w-full flex items-center justify-between px-6 bg-card border-b border-border z-20">
        {/* Left: Workspace */}
        <div className="flex items-center gap-3">
          {activeProject ? (
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-lg bg-primary/10 flex items-center justify-center">
                <span className="text-xs font-bold text-primary">
                  {activeProject.name.charAt(0).toUpperCase()}
                </span>
              </div>
              <div>
                <span className="text-sm font-semibold text-foreground block leading-none">
                  {activeProject.name}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {activeProject.status || 'Draft'}
                </span>
              </div>
            </div>
          ) : (
            <span className="text-sm font-medium text-muted-foreground">
              Select a workspace
            </span>
          )}
        </div>

        {/* Center: Search */}
        <div className="flex-1 max-w-md mx-6 hidden md:block">
          <button
            onClick={() => setSearchOpen(true)}
            className="flex items-center w-full h-9 px-3 rounded-lg border border-border bg-muted/50 text-muted-foreground hover:bg-muted transition-colors cursor-pointer"
          >
            <Search className="h-4 w-4 mr-2 shrink-0" />
            <span className="text-sm flex-1 text-left">Search...</span>
            <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-background border border-border text-[10px] font-mono">
              <Command className="h-2.5 w-2.5" />K
            </kbd>
          </button>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-1">
          {activeProject && (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleShare}
                disabled={shareStatus === 'loading'}
                className="gap-1.5"
              >
                {shareStatus === 'loading' ? (
                  <span className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                ) : shareStatus === 'success' ? (
                  <Check className="h-4 w-4 text-emerald-500" />
                ) : (
                  <Share2 className="h-4 w-4" />
                )}
                <span className="hidden sm:inline">
                  {shareStatus === 'success' ? 'Copied!' : 'Share'}
                </span>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleExport}
                disabled={exportStatus === 'loading'}
                className="gap-1.5"
              >
                {exportStatus === 'loading' ? (
                  <span className="h-4 w-4 rounded-full border-2 border-muted-foreground border-t-transparent animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                <span className="hidden sm:inline">Export</span>
              </Button>
            </>
          )}

          {/* Notifications */}
          <div className="relative" ref={notificationsRef}>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setNotificationsOpen(!notificationsOpen)}
              className="relative"
            >
              <Bell className="h-4 w-4" />
              {notifications.length > 0 && (
                <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-primary" />
              )}
            </Button>

            {notificationsOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-card border border-border rounded-xl shadow-xl py-2 z-30 animate-slide-down">
                <div className="px-4 py-2 border-b border-border">
                  <span className="text-overline">Activity</span>
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {notifications.map(n => (
                    <button
                      key={n.id}
                      onClick={() => {
                        setActiveStage(n.stage);
                        setNotificationsOpen(false);
                      }}
                      className="w-full px-4 py-3 hover:bg-muted transition-colors text-left border-b border-border/50 last:border-0"
                    >
                      <span className="text-sm text-foreground block">{n.text}</span>
                      <span className="text-xs text-muted-foreground mt-0.5 block">{n.time}</span>
                    </button>
                  ))}
                  {notifications.length === 0 && (
                    <div className="py-8 text-center text-sm text-muted-foreground">
                      No activity yet
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Profile */}
          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setProfileOpen(!profileOpen)}
              className="h-8 w-8 rounded-full bg-muted border border-border overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary/20 transition-all"
            >
              <img
                src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&q=80"
                alt="User avatar"
                className="h-full w-full object-cover"
              />
            </button>

            {profileOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-card border border-border rounded-xl shadow-xl py-2 z-30 animate-slide-down">
                <div className="px-4 py-3 border-b border-border">
                  <span className="text-sm font-semibold text-foreground block">{settings.founderName}</span>
                  <span className="text-xs text-muted-foreground block">{settings.founderTitle}</span>
                </div>
                <div className="py-1">
                  <button
                    onClick={() => {
                      setProfileOpen(false);
                      setSettingsOpen(true);
                    }}
                    className="w-full text-left px-4 py-2.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground flex items-center gap-2 transition-colors"
                  >
                    <Settings className="h-4 w-4" />
                    Settings
                  </button>
                  <button
                    onClick={() => {
                      logout();
                      setProfileOpen(false);
                    }}
                    className="w-full text-left px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2 transition-colors"
                  >
                    <LogOut className="h-4 w-4" />
                    Log Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Command Palette */}
      {searchOpen && (
        <div 
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-start justify-center pt-[20vh] px-4 animate-fade-in"
          onClick={() => setSearchOpen(false)}
        >
          <div 
            className="w-full max-w-lg bg-card border border-border rounded-2xl shadow-2xl overflow-hidden animate-scale-in"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center px-4 border-b border-border">
              <Search className="h-5 w-5 text-muted-foreground mr-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search projects, features, tasks..."
                autoFocus
                className="w-full h-14 bg-transparent text-base outline-none text-foreground placeholder-muted-foreground border-0"
              />
              <kbd className="text-xs text-muted-foreground border border-border px-2 py-1 rounded bg-muted">
                ESC
              </kbd>
            </div>

            <div className="max-h-[400px] overflow-y-auto p-2">
              {searchResults.map(res => (
                <button
                  key={res.id}
                  onClick={() => {
                    setActiveProject(res.projectId);
                    setActiveStage(res.stage);
                    setSearchOpen(false);
                    setSearchQuery('');
                  }}
                  className="w-full flex items-center gap-3 px-3 py-3 rounded-lg hover:bg-muted transition-colors text-left"
                >
                  <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
                    {res.type === 'project' && <Folder className="h-4 w-4" />}
                    {res.type === 'feature' && <Cpu className="h-4 w-4" />}
                    {res.type === 'task' && <Clock className="h-4 w-4" />}
                    {res.type === 'dna' && <TrendingUp className="h-4 w-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-foreground block truncate">{res.title}</span>
                    <span className="text-xs text-muted-foreground block truncate">{res.subtitle}</span>
                  </div>
                </button>
              ))}

              {searchQuery && searchResults.length === 0 && (
                <div className="py-12 text-center text-sm text-muted-foreground">
                  No results found
                </div>
              )}

              {!searchQuery && (
                <div className="py-8 text-center">
                  <span className="text-xs text-muted-foreground block mb-3">Quick Access</span>
                  <div className="flex flex-wrap gap-2 justify-center px-4">
                    {[
                      { name: 'DNA', stage: 'dna-analyzer' },
                      { name: 'Features', stage: 'feature-extractor' },
                      { name: 'Roadmap', stage: 'roadmap' },
                      { name: 'Team', stage: 'team-structure' },
                      { name: 'SWOT', stage: 'swot' },
                      { name: 'Costs', stage: 'cost-estimator' },
                    ].map(stg => (
                      <button
                        key={stg.stage}
                        onClick={() => {
                          setActiveStage(stg.stage as StageName);
                          setSearchOpen(false);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-muted hover:bg-muted/80 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {stg.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
