// global type definitions for the Start-up Evolution Engine workspace

export type StageName =
  | 'dna-analyzer'
  | 'feature-extractor'
  | 'roadmap'
  | 'team-structure'
  | 'swot'
  | 'cost-estimator'
  | 'final-blueprint';

export interface StartupDNA {
  category: string;
  industry: string;
  businessModel: string;
  targetMarket: string;
  valueProposition: string;
  usp: string;
  summary: string;
  scores: {
    innovation: number;
    scalability: number;
    complexity: number;
    opportunity: number;
    risk: number;
    competition: number;
  };
  recommendations: string[];
  confidence: number;
  assumptions: string[];
  nextSteps: string[];
}

export interface ProductFeature {
  id: string;
  name: string;
  description: string;
  category: 'auth' | 'core' | 'ai' | 'payments' | 'analytics' | 'growth' | 'ops' | 'misc';
  priority: 'critical' | 'high' | 'medium' | 'low' | 'optional';
  complexity: 'low' | 'medium' | 'high';
  dependencies: string[]; // IDs of other features
  benefits: string;
  risks: string;
}

export interface FeatureExtraction {
  totalFeatures: number;
  complexityScore: 'low' | 'medium' | 'high';
  features: ProductFeature[];
  mvpFeatureIds: string[];
  aiRecommendations: string[];
}

export interface RoadmapTask {
  id: string;
  name: string;
  durationWeeks: number;
  dependencies: string[];
}

export interface RoadmapPhase {
  id: string;
  name: string;
  durationWeeks: number;
  startWeek: number;
  endWeek: number;
  deliverables: string[];
  milestones: string[];
  tasks: RoadmapTask[];
  kpis: string[];
}

export interface ExecutionRoadmap {
  totalDurationWeeks: number;
  readinessScore: number;
  phases: RoadmapPhase[];
  growthStrategy: string[];
  recommendations: string[];
}

export interface TeamRole {
  id: string;
  name: string;
  department: 'engineering' | 'product' | 'design' | 'marketing' | 'sales' | 'ops' | 'cs' | 'ai';
  importance: 'critical' | 'high' | 'medium' | 'low';
  hiringStage: 'immediate' | 'pre-mvp' | 'pre-launch' | 'growth' | 'optional';
  responsibilities: string[];
  skills: string[];
  monthlyCost: number;
  dependencies: string[]; // Role IDs this reports to or coordinates with
}

export interface OrgStructure {
  recommendedTeamSize: number;
  orgChart: any[];
  roles: TeamRole[];
  raciMatrix?: Record<string, Record<string, 'R' | 'A' | 'C' | 'I'>>; // Role ID -> Task -> RACI Tag
  riskAnalysis?: string[];
  recommendations?: string[];
}

export interface SWOTItem {
  id: string;
  type: 'strength' | 'weakness' | 'opportunity' | 'threat';
  content: string;
  priority: 'high' | 'medium' | 'low';
  urgency: 'high' | 'medium' | 'low';
}

export interface SWOTAnalysis {
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  threats: string[];
  mitigations: { risk: string; mitigation: string }[];
  founderActions?: { timeline: string; tasks: string[] }[];
}

export interface CostItem {
  name: string;
  amount: number;
  category: 'development' | 'infrastructure' | 'team' | 'marketing' | 'ops' | 'legal' | 'misc';
  frequency: 'one-time' | 'monthly';
}

export interface BudgetScenario {
  id: 'lean' | 'balanced' | 'aggressive';
  name: string;
  mvpCost: number;
  year1Cost: number;
  monthlyBurn: number;
  runwayMonths: number;
  description: string;
}

export interface CostEstimation {
  mvpCost: number;
  launchCost: number;
  year1Cost: number;
  fundingRequirement: number;
  riskLevel: 'low' | 'medium' | 'high';
  readinessRating: number;
  costItems: CostItem[];
  scenarios: BudgetScenario[];
  recommendations: string[];
}

export interface CostEstimation {
  mvp_cost_estimate: number;
  year_1_cost_estimate: number;
  funding_requirements: any;
  budget_scenarios: any[];
  operational_costs: any;
}

export interface StartupProject {
  id: string;
  name: string;
  ideaPrompt: string;
  currentStage: StageName;
  status: 'idle' | 'generating' | 'completed' | 'error';
  dna?: StartupDNA;
  features?: FeatureExtraction;
  roadmap?: ExecutionRoadmap;
  team?: OrgStructure;
  swot?: SWOTAnalysis;
  cost?: CostEstimation;
  blueprintCompiled?: boolean;
  createdAt: string;
}
