'use client';

import React from 'react';
import { useSettingsStore } from '@/store/use-settings-store';
import { useBlueprintStore } from '@/store/use-blueprint-store';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  User, 
  Cpu, 
  DollarSign, 
  Trash2, 
  Sun, 
  Moon, 
  HelpCircle,
  Sliders,
  ShieldAlert
} from 'lucide-react';

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const settings = useSettingsStore();
  const { projects, deleteProject } = useBlueprintStore();
  const [resetConfirm, setResetConfirm] = React.useState(false);
  const [isResetting, setIsResetting] = React.useState(false);

  const handleResetWorkspace = async () => {
    setIsResetting(true);
    try {
      // Delete all projects in current store
      for (const project of projects) {
        await deleteProject(project.id);
      }
      settings.resetSettings();
      setResetConfirm(false);
      onOpenChange(false);
    } catch (err) {
      console.error('Failed to reset workspace:', err);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px] bg-card/95 backdrop-blur-md border border-border shadow-lvl-3 rounded-xl p-0 overflow-hidden">
        <DialogHeader className="p-6 pb-2">
          <DialogTitle className="text-xl font-bold tracking-tight text-primary flex items-center gap-2">
            <Sliders className="h-5 w-5 text-primary" />
            <span>Workspace Settings</span>
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Configure founder profiles, AI orchestration behavior, financial symbols, and workspace data.
          </DialogDescription>
        </DialogHeader>

        <div className="px-6 py-2">
          <Tabs defaultValue="general" className="w-full">
            <TabsList variant="line" className="w-full justify-start border-b border-border/40 pb-0 mb-4">
              <TabsTrigger value="general" className="flex items-center gap-1.5 py-2">
                <User className="h-3.5 w-3.5" />
                <span>Founder</span>
              </TabsTrigger>
              <TabsTrigger value="ai" className="flex items-center gap-1.5 py-2">
                <Cpu className="h-3.5 w-3.5" />
                <span>AI Models</span>
              </TabsTrigger>
              <TabsTrigger value="financial" className="flex items-center gap-1.5 py-2">
                <DollarSign className="h-3.5 w-3.5" />
                <span>Financials</span>
              </TabsTrigger>
              <TabsTrigger value="danger" className="flex items-center gap-1.5 py-2 text-red-500 hover:text-red-600 data-active:text-red-500 data-active:after:bg-red-500">
                <Trash2 className="h-3.5 w-3.5" />
                <span>Danger Zone</span>
              </TabsTrigger>
            </TabsList>

            {/* TAB 1: GENERAL/FOUNDER */}
            <TabsContent value="general" className="space-y-4 py-2">
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-[11px] font-semibold text-muted-foreground uppercase">Founder Name</label>
                    <Input
                      type="text"
                      value={settings.founderName}
                      onChange={(e) => settings.updateSettings({ founderName: e.target.value })}
                      placeholder="Founder Name"
                      className="h-9 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[11px] font-semibold text-muted-foreground uppercase">Founder Title</label>
                    <Input
                      type="text"
                      value={settings.founderTitle}
                      onChange={(e) => settings.updateSettings({ founderTitle: e.target.value })}
                      placeholder="e.g. CEO & CTO"
                      className="h-9 text-xs"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground uppercase">Interface Theme</label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => settings.updateSettings({ theme: 'light' })}
                      className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs border rounded-lg transition-all cursor-pointer ${
                        settings.theme === 'light'
                          ? 'bg-primary/5 border-primary/50 text-primary font-medium'
                          : 'border-border/60 bg-card hover:bg-muted/40'
                      }`}
                    >
                      <Sun className="h-4 w-4" />
                      <span>Light Theme</span>
                    </button>
                    <button
                      onClick={() => settings.updateSettings({ theme: 'dark' })}
                      className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs border rounded-lg transition-all cursor-pointer ${
                        settings.theme === 'dark'
                          ? 'bg-primary/10 border-primary/50 text-primary font-medium'
                          : 'border-border/60 bg-card hover:bg-muted/40'
                      }`}
                    >
                      <Moon className="h-4 w-4" />
                      <span>Dark Theme</span>
                    </button>
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* TAB 2: AI PARAMETERS */}
            <TabsContent value="ai" className="space-y-4 py-2">
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground uppercase flex items-center justify-between">
                    <span>Orchestrator Foundation Model</span>
                    <span className="text-[10px] text-primary/80 lowercase italic font-normal">SDK auto-failover active</span>
                  </label>
                  <Select
                    value={settings.model}
                    onValueChange={(val) => settings.updateSettings({ model: val || 'gemini-2.0-flash' })}
                  >
                    <SelectTrigger className="h-9 text-xs">
                      <SelectValue placeholder="Select model" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="gemini-2.0-flash">Gemini 2.0 Flash (Fastest / Recommended)</SelectItem>
                      <SelectItem value="gemini-2.0-flash-lite">Gemini 2.0 Flash-Lite (Low latency)</SelectItem>
                      <SelectItem value="gemini-1.5-flash">Gemini 1.5 Flash (Legacy stable)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between items-center">
                    <label className="text-[11px] font-semibold text-muted-foreground uppercase">AI Generation Temperature</label>
                    <span className="text-xs font-mono font-bold text-primary">{settings.temperature}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={settings.temperature}
                    onChange={(e) => settings.updateSettings({ temperature: parseFloat(e.target.value) })}
                    className="w-full h-1 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                  <div className="flex justify-between text-[10px] text-muted-foreground">
                    <span>Deterministic (0.0)</span>
                    <span>Creative (1.0)</span>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground uppercase flex items-center gap-1">
                    <span>Custom Gemini API Key</span>
                    <span className="text-[9px] text-muted-foreground lowercase italic font-normal">(stored locally)</span>
                  </label>
                  <Input
                    type="password"
                    value={settings.customApiKey}
                    onChange={(e) => settings.updateSettings({ customApiKey: e.target.value })}
                    placeholder="Enter custom GEMINI_API_KEY..."
                    className="h-9 text-xs"
                  />
                </div>
              </div>
            </TabsContent>

            {/* TAB 3: FINANCIAL PREFERENCES */}
            <TabsContent value="financial" className="space-y-4 py-2">
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground uppercase">Currency Symbol</label>
                  <Select
                    value={settings.currencySymbol}
                    onValueChange={(val) => settings.updateSettings({ currencySymbol: val || '$' })}
                  >
                    <SelectTrigger className="h-9 text-xs">
                      <SelectValue placeholder="Select currency" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="$">USD ($) Dollar</SelectItem>
                      <SelectItem value="€">EUR (€) Euro</SelectItem>
                      <SelectItem value="₹">INR (₹) Rupee</SelectItem>
                      <SelectItem value="£">GBP (£) Pound Sterling</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between items-center">
                    <label className="text-[11px] font-semibold text-muted-foreground uppercase">Cost Contingency Buffer</label>
                    <span className="text-xs font-mono font-bold text-primary">+{settings.costBuffer}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="50"
                    step="5"
                    value={settings.costBuffer}
                    onChange={(e) => settings.updateSettings({ costBuffer: parseInt(e.target.value) })}
                    className="w-full h-1 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                  <div className="flex justify-between text-[10px] text-muted-foreground">
                    <span>Direct AI Estimate (0%)</span>
                    <span>Conservative (+50%)</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground leading-relaxed pt-1">
                    Adds a safety contingency margin to all dynamic financial items, payroll tables, and scenario projections.
                  </p>
                </div>
              </div>
            </TabsContent>

            {/* TAB 4: DANGER ZONE */}
            <TabsContent value="danger" className="space-y-4 py-2">
              <div className="border border-red-500/20 rounded-lg p-4 bg-red-500/5 space-y-3">
                <div className="flex items-start gap-2">
                  <ShieldAlert className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-xs font-bold text-red-700 dark:text-red-400">Reset Local Workspace</h4>
                    <p className="text-[10px] text-red-600/80 dark:text-red-400/80 leading-relaxed mt-0.5">
                      This action will permanently delete all created startup projects and compiled blueprints from your user session. This cannot be undone.
                    </p>
                  </div>
                </div>

                {resetConfirm ? (
                  <div className="flex items-center gap-2 pt-1">
                    <Button
                      variant="destructive"
                      onClick={handleResetWorkspace}
                      disabled={isResetting}
                      size="sm"
                      className="text-xs h-8"
                    >
                      {isResetting ? 'Wiping Workspace...' : 'Confirm Permanent Reset'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setResetConfirm(false)}
                      size="sm"
                      className="text-xs h-8 border-border"
                    >
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="destructive"
                    onClick={() => setResetConfirm(true)}
                    size="sm"
                    className="text-xs h-8 w-full"
                  >
                    Wipe All Projects & Reset Config
                  </Button>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>

        <DialogFooter className="mt-6 border-t border-border/40 p-4 bg-muted/40">
          <Button
            onClick={() => onOpenChange(false)}
            className="text-xs h-8 px-6"
          >
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
