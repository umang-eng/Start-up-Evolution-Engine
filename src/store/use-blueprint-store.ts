import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { StartupProject, StageName, StartupDNA, FeatureExtraction, ExecutionRoadmap, OrgStructure, SWOTAnalysis, CostEstimation } from '@/types/blueprint';

interface BlueprintState {
  projects: StartupProject[];
  activeProjectId: string | null;
  sidebarOpen: boolean;
  activeStage: StageName;
  
  // Actions
  toggleSidebar: () => void;
  setActiveStage: (stage: StageName) => void;
  setActiveProject: (id: string) => void;
  createNewProject: (name: string, prompt: string) => StartupProject;
  updateProjectStatus: (id: string, status: StartupProject['status']) => void;
  updateProjectStage: (id: string, stage: StageName) => void;
  
  // Save section data
  saveDNA: (projectId: string, dna: StartupDNA) => void;
  saveFeatures: (projectId: string, features: FeatureExtraction) => void;
  saveRoadmap: (projectId: string, roadmap: ExecutionRoadmap) => void;
  saveTeam: (projectId: string, team: OrgStructure) => void;
  saveSWOT: (projectId: string, swot: SWOTAnalysis) => void;
  saveCost: (projectId: string, cost: CostEstimation) => void;
}

export const useBlueprintStore = create<BlueprintState>()(
  persist(
    (set) => ({
      projects: [],
      activeProjectId: null,
      sidebarOpen: true,
      activeStage: 'dna-analyzer',
      
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      
      setActiveStage: (stage) => set({ activeStage: stage }),
      
      setActiveProject: (id) => set((state) => {
        const proj = state.projects.find((p) => p.id === id);
        return {
          activeProjectId: id,
          activeStage: proj ? proj.currentStage : 'dna-analyzer'
        };
      }),
      
      createNewProject: (name, prompt) => {
        const newProj: StartupProject = {
          id: crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 9),
          name: name || 'My Startup Project',
          ideaPrompt: prompt,
          currentStage: 'dna-analyzer',
          status: 'idle',
          createdAt: new Date().toISOString()
        };
        
        set((state) => ({
          projects: [newProj, ...state.projects],
          activeProjectId: newProj.id,
          activeStage: 'dna-analyzer'
        }));
        
        return newProj;
      },
      
      updateProjectStatus: (id, status) => set((state) => ({
        projects: state.projects.map((p) => p.id === id ? { ...p, status } : p)
      })),
      
      updateProjectStage: (id, stage) => set((state) => ({
        projects: state.projects.map((p) => p.id === id ? { ...p, currentStage: stage } : p)
      })),
      
      saveDNA: (projectId, dna) => set((state) => ({
        projects: state.projects.map((p) => p.id === projectId ? { ...p, dna, currentStage: 'feature-extractor' } : p),
        activeStage: 'feature-extractor'
      })),
      
      saveFeatures: (projectId, features) => set((state) => ({
        projects: state.projects.map((p) => p.id === projectId ? { ...p, features, currentStage: 'roadmap' } : p),
        activeStage: 'roadmap'
      })),
      
      saveRoadmap: (projectId, roadmap) => set((state) => ({
        projects: state.projects.map((p) => p.id === projectId ? { ...p, roadmap, currentStage: 'team-structure' } : p),
        activeStage: 'team-structure'
      })),
      
      saveTeam: (projectId, team) => set((state) => ({
        projects: state.projects.map((p) => p.id === projectId ? { ...p, team, currentStage: 'swot' } : p),
        activeStage: 'swot'
      })),
      
      saveSWOT: (projectId, swot) => set((state) => ({
        projects: state.projects.map((p) => p.id === projectId ? { ...p, swot, currentStage: 'cost-estimator' } : p),
        activeStage: 'cost-estimator'
      })),
      
      saveCost: (projectId, cost) => set((state) => ({
        projects: state.projects.map((p) => p.id === projectId ? { ...p, cost, currentStage: 'final-blueprint' } : p),
        activeStage: 'final-blueprint'
      }))
    }),
    {
      name: 'blueprint-store',
      partialize: (state) => ({
        projects: state.projects,
        activeProjectId: state.activeProjectId
      })
    }
  )
);
