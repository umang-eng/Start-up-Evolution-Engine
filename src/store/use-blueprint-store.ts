import { create } from 'zustand';
import { 
  StartupProject, 
  StageName, 
  StartupDNA, 
  FeatureExtraction, 
  ExecutionRoadmap, 
  OrgStructure, 
  SWOTAnalysis, 
  CostEstimation,
  LegalComplianceResult,
  CompetitiveMoatResult,
  StressTestResult,
  FinancialIntelligenceResult,
  InvestmentCommitteeResult,
  ProductExecutionResult,
  GlobalExpansionResult
} from '@/types/blueprint';
import { 
  api, mapDnaResponse, mapFeaturesResponse, mapRoadmapResponse, mapTeamResponse, 
  mapSwotResponse, mapCostResponse,
  mapLegalComplianceResponse, mapCompetitiveMoatResponse, mapStressTestResponse,
  mapFinancialIntelligenceResponse, mapInvestmentCommitteeResponse,
  mapProductExecutionResponse, mapGlobalExpansionResponse
} from '@/lib/api-client';

interface BlueprintState {
  projects: StartupProject[];
  activeProjectId: string | null;
  sidebarOpen: boolean;
  activeStage: StageName;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  toggleSidebar: () => void;
  setActiveStage: (stage: StageName) => void;
  setActiveProject: (id: string) => void;
  loadProjects: () => Promise<void>;
  createNewProject: (name: string, prompt: string) => Promise<StartupProject>;
  deleteProject: (id: string) => Promise<void>;
  updateProjectStatus: (id: string, status: StartupProject['status']) => void;
  updateProjectStage: (id: string, stage: StageName) => void;
  loadBlueprint: (projectId: string) => Promise<void>;
  
  // Save section data dynamically
  saveDNA: (projectId: string, dna: StartupDNA) => void;
  saveFeatures: (projectId: string, features: FeatureExtraction) => void;
  saveRoadmap: (projectId: string, roadmap: ExecutionRoadmap) => void;
  saveTeam: (projectId: string, team: OrgStructure) => void;
  saveSWOT: (projectId: string, swot: SWOTAnalysis) => void;
  saveCost: (projectId: string, cost: CostEstimation) => void;
  saveLegalCompliance: (projectId: string, data: LegalComplianceResult) => void;
  saveCompetitiveMoat: (projectId: string, data: CompetitiveMoatResult) => void;
  saveStressTest: (projectId: string, data: StressTestResult) => void;
  saveFinancialIntelligence: (projectId: string, data: FinancialIntelligenceResult) => void;
  saveInvestmentCommittee: (projectId: string, data: InvestmentCommitteeResult) => void;
  saveProductExecution: (projectId: string, data: ProductExecutionResult) => void;
  saveGlobalExpansion: (projectId: string, data: GlobalExpansionResult) => void;
}

export const useBlueprintStore = create<BlueprintState>()((set, get) => ({
  projects: [],
  activeProjectId: null,
  sidebarOpen: true,
  activeStage: 'dna-analyzer',
  isLoading: false,
  error: null,
  
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  
  setActiveStage: (stage) => set({ activeStage: stage }),
  
  setActiveProject: (id) => set((state) => {
    const proj = state.projects.find((p) => p.id === id);
    return {
      activeProjectId: id,
      activeStage: proj ? proj.currentStage : 'dna-analyzer'
    };
  }),
  
  loadProjects: async () => {
    set({ isLoading: true, error: null });
    try {
      const result = await api.projects.list();
      // Result data returned is direct ProjectResponse list
      const projects: StartupProject[] = result.map((p: any) => ({
        id: p.id,
        name: p.title,
        ideaPrompt: p.description || '',
        currentStage: 'dna-analyzer',
        status: 'idle',
        createdAt: p.created_at,
      }));
      set({ projects, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to load projects', isLoading: false });
    }
  },
  
  createNewProject: async (name, prompt) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.projects.create({
        title: name || 'My Startup Project',
        description: prompt,
        industry: 'Tech'
      });

      const newProj: StartupProject = {
        id: response.id,
        name: response.title,
        ideaPrompt: response.description || '',
        currentStage: 'dna-analyzer',
        status: 'idle',
        createdAt: response.created_at
      };

      set((state) => ({
        projects: [newProj, ...state.projects],
        activeProjectId: newProj.id,
        activeStage: 'dna-analyzer',
        isLoading: false
      }));

      return newProj;
    } catch (err: any) {
      set({ error: err.message || 'Failed to create project', isLoading: false });
      throw err;
    }
  },

  deleteProject: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await api.projects.delete(id);
      set((state) => {
        const remaining = state.projects.filter(p => p.id !== id);
        const nextActive = remaining.length > 0 ? remaining[0].id : null;
        return {
          projects: remaining,
          activeProjectId: nextActive,
          activeStage: nextActive ? (remaining[0].currentStage || 'dna-analyzer') : 'dna-analyzer',
          isLoading: false
        };
      });
    } catch (err: any) {
      set({ error: err.message || 'Failed to delete project', isLoading: false });
      throw err;
    }
  },
  
  updateProjectStatus: (id, status) => set((state) => ({
    projects: state.projects.map((p) => p.id === id ? { ...p, status } : p)
  })),
  
  updateProjectStage: (id, stage) => set((state) => ({
    projects: state.projects.map((p) => p.id === id ? { ...p, currentStage: stage } : p)
  })),

  loadBlueprint: async (projectId) => {
    try {
      const blueprintData = await api.blueprints.get(projectId, true);
      if (!blueprintData) return;

      const dna = mapDnaResponse(blueprintData.startup_dna);
      const features = mapFeaturesResponse(blueprintData.product_architecture);
      const roadmap = mapRoadmapResponse(blueprintData.execution_roadmap);
      const team = mapTeamResponse(blueprintData.team_structure);
      const swot = mapSwotResponse(blueprintData.swot_analysis);
      const cost = mapCostResponse(blueprintData.financial_plan);
      const legalCompliance = mapLegalComplianceResponse(blueprintData.legal_compliance);
      const competitiveMoat = mapCompetitiveMoatResponse(blueprintData.competitive_moat);
      const stressTest = mapStressTestResponse(blueprintData.stress_test);
      const financialIntelligence = mapFinancialIntelligenceResponse(blueprintData.financial_intelligence);
      const investmentCommittee = mapInvestmentCommitteeResponse(blueprintData.investment_committee);
      const productExecution = mapProductExecutionResponse(blueprintData.product_execution);
      const globalExpansion = mapGlobalExpansionResponse(blueprintData.global_expansion);

      // Determine the compilation completion status and current stage
      const hasFullBlueprint = !!blueprintData.executive_summary || !!blueprintData.health_indicators;
      
      let resolvedStage: StageName = 'dna-analyzer';
      let resolvedStatus: StartupProject['status'] = 'idle';
      let resolvedCompiled = false;

      // Determine highest completed stage
      if (globalExpansion) {
        resolvedStage = 'global-expansion';
      } else if (productExecution) {
        resolvedStage = 'product-execution';
      } else if (investmentCommittee) {
        resolvedStage = 'investment-committee';
      } else if (financialIntelligence) {
        resolvedStage = 'financial-intelligence';
      } else if (stressTest) {
        resolvedStage = 'stress-test';
      } else if (competitiveMoat) {
        resolvedStage = 'competitive-moat';
      } else if (legalCompliance) {
        resolvedStage = 'legal-compliance';
      } else if (hasFullBlueprint) {
        resolvedStage = 'final-blueprint';
        resolvedStatus = 'completed';
        resolvedCompiled = true;
      } else if (cost) {
        resolvedStage = 'final-blueprint';
      } else if (swot) {
        resolvedStage = 'cost-estimator';
      } else if (team) {
        resolvedStage = 'swot';
      } else if (roadmap) {
        resolvedStage = 'team-structure';
      } else if (features) {
        resolvedStage = 'roadmap';
      } else if (dna) {
        resolvedStage = 'feature-extractor';
      }

      set((state) => {
        const isCurrentlyActive = state.activeProjectId === projectId;
        return {
          projects: state.projects.map((p) => p.id === projectId ? {
            ...p,
            dna,
            features,
            roadmap,
            team,
            swot,
            cost,
            legalCompliance,
            competitiveMoat,
            stressTest,
            financialIntelligence,
            investmentCommittee,
            productExecution,
            globalExpansion,
            status: p.status === 'completed' && !hasFullBlueprint ? 'idle' : (resolvedStatus || p.status),
            currentStage: resolvedStage,
            blueprintCompiled: resolvedCompiled
          } : p),
          activeStage: isCurrentlyActive ? resolvedStage : state.activeStage
        };
      });
    } catch (err) {
      console.error('Failed to load compiled blueprint:', err);
    }
  },
  
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
  })),

  saveLegalCompliance: (projectId, data) => set((state) => ({
    projects: state.projects.map((p) => p.id === projectId ? { ...p, legalCompliance: data } : p),
  })),

  saveCompetitiveMoat: (projectId, data) => set((state) => ({
    projects: state.projects.map((p) => p.id === projectId ? { ...p, competitiveMoat: data } : p),
  })),

  saveStressTest: (projectId, data) => set((state) => ({
    projects: state.projects.map((p) => p.id === projectId ? { ...p, stressTest: data } : p),
  })),

  saveFinancialIntelligence: (projectId, data) => set((state) => ({
    projects: state.projects.map((p) => p.id === projectId ? { ...p, financialIntelligence: data } : p),
  })),

  saveInvestmentCommittee: (projectId, data) => set((state) => ({
    projects: state.projects.map((p) => p.id === projectId ? { ...p, investmentCommittee: data } : p),
  })),

  saveProductExecution: (projectId, data) => set((state) => ({
    projects: state.projects.map((p) => p.id === projectId ? { ...p, productExecution: data } : p),
  })),

  saveGlobalExpansion: (projectId, data) => set((state) => ({
    projects: state.projects.map((p) => p.id === projectId ? { ...p, globalExpansion: data } : p),
  })),
}));
