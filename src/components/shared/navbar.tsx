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
  TrendingUp
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export function Navbar() {
  const { projects, activeProjectId, setActiveStage } = useBlueprintStore();
  const { user, logout } = useAuth();
  
  const activeProject = projects.find(p => p.id === activeProjectId);

  // UI States
  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  const [shareStatus, setShareStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [exportStatus, setExportStatus] = useState<'idle' | 'loading'>('idle');

  // Refs for closing dropdowns when clicking outside
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

  // Keyboard shortcut for Search (⌘K)
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

  // Handle Share link generation
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

  // Handle PDF Export
  const handleExport = () => {
    if (!activeProject) return;
    setExportStatus('loading');
    window.open(api.exports.pdf(activeProject.id), '_blank');
    setTimeout(() => setExportStatus('idle'), 1500);
  };

  // Generate dynamic search results
  const getSearchResults = () => {
    if (!activeProject || !searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase();
    const results: Array<{
      id: string;
      title: string;
      subtitle: string;
      stage: StageName;
      type: 'feature' | 'task' | 'role' | 'cost' | 'dna';
    }> = [];

    // Search DNA
    if (activeProject.dna) {
      const dna = activeProject.dna;
      if (
        dna.category.toLowerCase().includes(q) ||
        dna.valueProposition.toLowerCase().includes(q) ||
        dna.usp.toLowerCase().includes(q)
      ) {
        results.push({
          id: 'dna-match',
          title: 'Strategic Moat & USP',
          subtitle: dna.usp.substring(0, 60) + '...',
          stage: 'dna-analyzer',
          type: 'dna'
        });
      }
    }

    // Search Features
    if (activeProject.features?.features) {
      activeProject.features.features.forEach(f => {
        if (f.name.toLowerCase().includes(q) || f.description.toLowerCase().includes(q)) {
          results.push({
            id: f.id,
            title: f.name,
            subtitle: `Priority: ${f.priority} • Complexity: ${f.complexity}`,
            stage: 'feature-extractor',
            type: 'feature'
          });
        }
      });
    }

    // Search Roadmap/Tasks
    if (activeProject.roadmap?.phases) {
      activeProject.roadmap.phases.forEach(p => {
        p.tasks.forEach(t => {
          if (t.name.toLowerCase().includes(q)) {
            results.push({
              id: t.id,
              title: t.name,
              subtitle: `Phase: ${p.name} • Duration: ${t.durationWeeks}w`,
              stage: 'roadmap',
              type: 'task'
            });
          }
        });
      });
    }

    // Search Team structure
    if (activeProject.team?.roles) {
      activeProject.team.roles.forEach(r => {
        if (r.name.toLowerCase().includes(q) || r.department.toLowerCase().includes(q)) {
          results.push({
            id: r.id,
            title: r.name,
            subtitle: `Dept: ${r.department} • Cost: $${r.monthlyCost.toLocaleString()}/mo`,
            stage: 'team-structure',
            type: 'role'
          });
        }
      });
    }

    // Search Costs
    if (activeProject.cost?.costItems) {
      activeProject.cost.costItems.forEach((c, idx) => {
        if (c.name.toLowerCase().includes(q) || c.category.toLowerCase().includes(q)) {
          results.push({
            id: `cost_${idx}`,
            title: c.name,
            subtitle: `Category: ${c.category} • Cost: $${c.amount.toLocaleString()}`,
            stage: 'cost-estimator',
            type: 'cost'
          });
        }
      });
    }

    return results;
  };

  const searchResults = getSearchResults();

  // Create notifications derived from active project stages completed
  const getNotifications = () => {
    if (!activeProject) return [];
    const logs: Array<{ id: string; text: string; time: string; stage: StageName }> = [];
    if (activeProject.dna) {
      logs.push({ id: 'n1', text: 'Venture DNA diagnostics structured.', time: 'Stage 1 Complete', stage: 'dna-analyzer' });
    }
    if (activeProject.features) {
      logs.push({ id: 'n2', text: 'PRD technical features spec compiled.', time: 'Stage 2 Complete', stage: 'feature-extractor' });
    }
    if (activeProject.roadmap) {
      logs.push({ id: 'n3', text: 'Week-by-week execution roadmap created.', time: 'Stage 3 Complete', stage: 'roadmap' });
    }
    if (activeProject.team) {
      logs.push({ id: 'n4', text: 'Resource salary model and chart defined.', time: 'Stage 4 Complete', stage: 'team-structure' });
    }
    if (activeProject.swot) {
      logs.push({ id: 'n5', text: 'Strategic SWOT board composed.', time: 'Stage 5 Complete', stage: 'swot' });
    }
    if (activeProject.cost) {
      logs.push({ id: 'n6', text: 'Financial burn scenarios projected.', time: 'Stage 6 Complete', stage: 'cost-estimator' });
    }
    return logs.reverse(); // Newest first
  };

  const notifications = getNotifications();

  return (
    <>
      <header className="h-14 w-full flex items-center justify-between px-6 bg-card/75 backdrop-blur-md border-b border-border shadow-lvl-1 z-20">
        {/* Left Workspace Switcher */}
        <div className="flex items-center gap-3">
          <div className="h-7 w-7 rounded-md bg-accent-blue flex items-center justify-center text-white text-[11px] font-bold shadow-lvl-1">
            SE
          </div>
          <div className="flex items-center gap-1.5 cursor-pointer hover:bg-black/5 px-2 py-1 rounded-md transition-all">
            <span className="text-xs font-semibold text-primary">
              {activeProject ? activeProject.name : 'Personal Workspace'}
            </span>
            <ChevronDown className="h-3 w-3 text-muted-foreground" />
          </div>
        </div>

        {/* Center Action Pipeline Search */}
        <div className="flex-1 max-w-md mx-6 hidden md:block">
          <div 
            onClick={() => setSearchOpen(true)}
            className="relative flex items-center w-full h-8 px-3 rounded-md border border-border/80 bg-surface-secondary text-muted-foreground hover:border-standard cursor-pointer transition-all"
          >
            <Search className="h-3.5 w-3.5 mr-2" />
            <span className="text-xs flex-1 text-left">Search blueprint features, costs...</span>
            <kbd className="h-5 px-1.5 rounded bg-black/5 border border-border text-[9px] font-sans flex items-center">
              ⌘K
            </kbd>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-2">
          {activeProject && (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleShare}
                disabled={shareStatus === 'loading'}
                className="h-8 text-xs gap-1.5 hover:bg-black/5 text-muted-foreground"
              >
                {shareStatus === 'loading' ? (
                  <span className="h-3.5 w-3.5 rounded-full border border-accent-blue border-t-transparent animate-spin" />
                ) : shareStatus === 'success' ? (
                  <Check className="h-3.5 w-3.5 text-green-500 animate-pulse" />
                ) : (
                  <Share2 className="h-3.5 w-3.5 text-accent-blue" />
                )}
                <span className="hidden sm:inline">
                  {shareStatus === 'success' ? 'Copied!' : shareStatus === 'error' ? 'Failed' : 'Share'}
                </span>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleExport}
                disabled={exportStatus === 'loading'}
                className="h-8 text-xs gap-1.5 hover:bg-black/5 text-muted-foreground"
              >
                {exportStatus === 'loading' ? (
                  <span className="h-3.5 w-3.5 rounded-full border border-muted-foreground border-t-transparent animate-spin" />
                ) : (
                  <Download className="h-3.5 w-3.5" />
                )}
                <span className="hidden sm:inline">
                  {exportStatus === 'loading' ? 'Exporting...' : 'Export'}
                </span>
              </Button>
            </>
          )}

          {/* Notifications Dropdown */}
          <div className="relative" ref={notificationsRef}>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setNotificationsOpen(!notificationsOpen)}
              className="h-8 w-8 hover:bg-black/5 text-muted-foreground relative"
            >
              <Bell className="h-4 w-4" />
              {notifications.length > 0 && (
                <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-accent-blue animate-pulse" />
              )}
            </Button>

            {notificationsOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-card border border-border rounded-lg shadow-lvl-3 py-2 z-30 animate-in fade-in slide-in-from-top-2 duration-150">
                <span className="text-[10px] font-bold text-muted-foreground uppercase px-4 pb-2 border-b border-border/60 block tracking-wider">
                  Activity Logs
                </span>
                <div className="max-h-60 overflow-y-auto mt-2">
                  {notifications.map(n => (
                    <div 
                      key={n.id}
                      onClick={() => {
                        setActiveStage(n.stage);
                        setNotificationsOpen(false);
                      }}
                      className="px-4 py-2 hover:bg-black/5 cursor-pointer transition-colors border-b border-border/40 last:border-0"
                    >
                      <span className="text-xs text-primary block font-medium">{n.text}</span>
                      <span className="text-[10px] text-muted-foreground block mt-0.5">{n.time}</span>
                    </div>
                  ))}
                  {notifications.length === 0 && (
                    <span className="text-xs text-muted-foreground/60 italic text-center block py-8">
                      No startup components evolved yet.
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* User Profile Avatar Dropdown */}
          <div className="relative" ref={profileRef}>
            <div 
              onClick={() => setProfileOpen(!profileOpen)}
              className="h-8 w-8 rounded-full border border-border overflow-hidden cursor-pointer hover:border-standard hover:scale-105 active:scale-95 transition-all"
            >
              <img
                src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&q=80"
                alt="User avatar"
                className="h-full w-full object-cover"
              />
            </div>

            {profileOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-card border border-border rounded-lg shadow-lvl-3 py-2 z-30 animate-in fade-in slide-in-from-top-2 duration-150">
                <div className="px-4 py-2 border-b border-border/60">
                  <span className="text-xs font-semibold text-primary block truncate">Founder Member</span>
                  <span className="text-[10px] text-muted-foreground block truncate">{user?.email || 'builder@test.com'}</span>
                </div>
                <div className="py-1">
                  <button
                    onClick={() => {
                      logout();
                      setProfileOpen(false);
                    }}
                    className="w-full text-left px-4 py-2 text-xs text-red-600 hover:bg-red-50 flex items-center gap-2 transition-colors border-0 cursor-pointer"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                    <span>Log Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Command Palette Search Overlay Dialog */}
      {searchOpen && (
        <div 
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-start justify-center pt-24 px-4 animate-in fade-in duration-200"
          onClick={() => setSearchOpen(false)}
        >
          <div 
            className="w-full max-w-lg bg-card border border-border rounded-xl shadow-lvl-3 overflow-hidden flex flex-col animate-in zoom-in-95 duration-200"
            onClick={e => e.stopPropagation()}
          >
            {/* Search Input */}
            <div className="flex items-center px-4 border-b border-border/60">
              <Search className="h-4 w-4 text-muted-foreground mr-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Type to search features, costs, roadmap tasks..."
                autoFocus
                className="w-full h-12 bg-transparent text-sm outline-none text-primary placeholder-muted-foreground/60 border-0"
              />
              <span className="text-[10px] text-muted-foreground/50 border border-border/60 px-1.5 py-0.5 rounded bg-black/5 select-none">
                ESC
              </span>
            </div>

            {/* Results Body */}
            <div className="max-h-[350px] overflow-y-auto p-2 space-y-1 scrollbar-thin">
              {searchResults.map(res => (
                <div
                  key={res.id}
                  onClick={() => {
                    setActiveStage(res.stage);
                    setSearchOpen(false);
                    setSearchQuery('');
                  }}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-black/5 cursor-pointer transition-colors"
                >
                  <div className="h-7 w-7 rounded bg-accent-blue/10 flex items-center justify-center text-accent-blue shrink-0">
                    {res.type === 'feature' && <Cpu className="h-3.5 w-3.5" />}
                    {res.type === 'task' && <Clock className="h-3.5 w-3.5" />}
                    {res.type === 'role' && <User className="h-3.5 w-3.5" />}
                    {res.type === 'cost' && <DollarSign className="h-3.5 w-3.5" />}
                    {res.type === 'dna' && <TrendingUp className="h-3.5 w-3.5" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-xs font-semibold text-primary block truncate text-left">{res.title}</span>
                    <span className="text-[10px] text-muted-foreground block truncate mt-0.5 text-left">{res.subtitle}</span>
                  </div>
                  <span className="text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-black/5 text-muted-foreground select-none shrink-0">
                    {res.stage.replace('-', ' ')}
                  </span>
                </div>
              ))}

              {searchQuery && searchResults.length === 0 && (
                <span className="text-xs text-muted-foreground/60 italic text-center block py-12">
                  No matching workspace records found.
                </span>
              )}

              {!searchQuery && (
                <div className="py-8 text-center text-xs text-muted-foreground space-y-3">
                  <span className="block font-medium">Quick Navigation</span>
                  <div className="flex flex-wrap gap-2 justify-center px-4">
                    {[
                      { name: 'DNA Analyzer', stage: 'dna-analyzer' },
                      { name: 'Feature Spec', stage: 'feature-extractor' },
                      { name: 'Timeline Roadmap', stage: 'roadmap' },
                      { name: 'Org Structure', stage: 'team-structure' },
                      { name: 'SWOT Assessment', stage: 'swot' },
                      { name: 'Burn Estimator', stage: 'cost-estimator' },
                      { name: 'Final Strategy', stage: 'final-blueprint' }
                    ].map(stg => (
                      <button
                        key={stg.stage}
                        onClick={() => {
                          setActiveStage(stg.stage as StageName);
                          setSearchOpen(false);
                        }}
                        className="px-2.5 py-1 rounded bg-black/5 hover:bg-black/10 text-[10px] font-semibold text-muted-foreground hover:text-primary transition-all cursor-pointer border-0"
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
    </>
  );
}
