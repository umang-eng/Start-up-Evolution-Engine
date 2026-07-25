// global type definitions for the Start-up Evolution Engine workspace

export type StageName =
  | 'dna-analyzer'
  | 'feature-extractor'
  | 'roadmap'
  | 'team-structure'
  | 'swot'
  | 'cost-estimator'
  | 'final-blueprint'
  | 'legal-compliance'
  | 'competitive-moat'
  | 'stress-test'
  | 'financial-intelligence'
  | 'investment-committee'
  | 'product-execution'
  | 'global-expansion';

export const ALL_STAGES: StageName[] = [
  'dna-analyzer',
  'feature-extractor',
  'roadmap',
  'team-structure',
  'swot',
  'cost-estimator',
  'final-blueprint',
  'legal-compliance',
  'competitive-moat',
  'stress-test',
  'financial-intelligence',
  'investment-committee',
  'product-execution',
  'global-expansion',
];

export const STAGE_LABELS: Record<StageName, string> = {
  'dna-analyzer': 'DNA Analyzer',
  'feature-extractor': 'Feature Extractor',
  'roadmap': 'Roadmap',
  'team-structure': 'Team Structure',
  'swot': 'SWOT Analysis',
  'cost-estimator': 'Cost Estimator',
  'final-blueprint': 'Final Blueprint',
  'legal-compliance': 'Legal & Compliance',
  'competitive-moat': 'Competitive Moat',
  'stress-test': 'Stress Test',
  'financial-intelligence': 'Financial Intelligence',
  'investment-committee': 'Investment Committee',
  'product-execution': 'Product Execution',
  'global-expansion': 'Global Expansion',
};

export const STAGE_ICONS: Record<StageName, string> = {
  'dna-analyzer': 'Dna',
  'feature-extractor': 'GitBranch',
  'roadmap': 'LineChart',
  'team-structure': 'Network',
  'swot': 'TrendingUp',
  'cost-estimator': 'Award',
  'final-blueprint': 'ScrollText',
  'legal-compliance': 'Shield',
  'competitive-moat': 'Target',
  'stress-test': 'Zap',
  'financial-intelligence': 'BarChart3',
  'investment-committee': 'Users',
  'product-execution': 'Rocket',
  'global-expansion': 'Globe',
};

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
  dependencies: string[];
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
  dependencies: string[];
}

export interface OrgStructure {
  recommendedTeamSize: number;
  roles: TeamRole[];
  raciMatrix: Record<string, Record<string, 'R' | 'A' | 'C' | 'I'>>;
  riskAnalysis: string[];
  recommendations: string[];
}

export interface SWOTItem {
  id: string;
  type: 'strength' | 'weakness' | 'opportunity' | 'threat';
  content: string;
  priority: 'high' | 'medium' | 'low';
  urgency: 'high' | 'medium' | 'low';
}

export interface SWOTAnalysis {
  healthScore: number;
  growthPotential: number;
  items: SWOTItem[];
  riskMatrix: {
    threatId: string;
    probability: 'high' | 'medium' | 'low';
    impact: 'high' | 'medium' | 'low';
    mitigation: string;
  }[];
  opportunityMatrix: {
    opportunityId: string;
    impact: 'high' | 'medium' | 'low';
    easeOfExecution: 'high' | 'medium' | 'low';
  }[];
  recommendations: string[];
  actionPlan: {
    immediate: string[];
    days30: string[];
    days60: string[];
    days90: string[];
  };
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

// ── Intelligence Stages (7-14) ──────────────────────────────────

export interface LegalComplianceResult {
  compliance_checklist: { item: string; status: 'compliant' | 'pending' | 'gap' | 'not_applicable'; notes: string }[];
  ip_protection: { asset: string; protection_type: string; status: string }[];
  regulatory_requirements: { regulation: string; applicability: string; action_needed: string }[];
  grants_incentives: { name: string; eligibility: string; value: string }[];
  registrations_needed: { type: string; jurisdiction: string; timeline: string }[];
  overall_risk: string;
  recommendations: string[];
}

export interface CompetitiveMoatResult {
  competitors: { name: string; strength: string; weakness: string; threat_level: string }[];
  moat_scores: { dimension: string; score: number; evidence: string }[];
  positioning: { category: string; differentiator: string; vulnerability: string }[];
  copy_difficulty: { factor: string; difficulty: string; explanation: string }[];
  overall_moat_strength: number;
  strategic_recommendations: string[];
}

export interface StressTestResult {
  scenarios: { name: string; description: string; probability: string; impact: string; mitigation: string; recovery_time: string }[];
  risk_scores: { risk: string; score: number; probability: string; impact: string }[];
  resilience_score: number;
  critical_dependencies: string[];
  recommendations: string[];
}

export interface FinancialIntelligenceResult {
  projections: { metric: string; month_1: number; month_6: number; month_12: number; month_24: number }[];
  unit_economics: { metric: string; value: number; benchmark: string }[];
  funding_analysis: { stage: string; amount: string; timeline: string; milestones_needed: string[] }[];
  valuation_model: { method: string; estimated_value: string; confidence: string }[];
  financial_health_score: number;
  recommendations: string[];
}

export interface InvestmentCommitteeResult {
  partner_cards: { name: string; role: string; vote: 'approve' | 'conditional' | 'reject' | 'abstain'; reasoning: string; concerns: string[] }[];
  investment_recommendation: string;
  term_sheet: { term: string; value: string }[];
  due_diligence: { area: string; status: 'pass' | 'flag' | 'fail'; notes: string }[];
  overall_score: number;
  conditions: string[];
}

export interface ProductExecutionResult {
  prd_summary: string;
  sprint_plan: { sprint: number; name: string; goals: string[]; duration_weeks: number }[];
  architecture: { component: string; technology: string; rationale: string }[];
  api_endpoints: { method: string; path: string; description: string }[];
  technical_debt: { item: string; severity: string; effort: string }[];
  launch_readiness: number;
  recommendations: string[];
}

export interface GlobalExpansionResult {
  target_markets: { country: string; market_size: string; growth_rate: string; entry_difficulty: string; priority: string }[];
  expansion_waves: { wave: number; markets: string[]; timeline: string; investment: string }[];
  localization: { market: string; language_requirements: string; cultural_adaptations: string[]; regulatory_notes: string[] }[];
  global_risks: { risk: string; region: string; probability: string; mitigation: string }[];
  total_addressable_market_global: string;
  recommendations: string[];
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
  legalCompliance?: LegalComplianceResult;
  competitiveMoat?: CompetitiveMoatResult;
  stressTest?: StressTestResult;
  financialIntelligence?: FinancialIntelligenceResult;
  investmentCommittee?: InvestmentCommitteeResult;
  productExecution?: ProductExecutionResult;
  globalExpansion?: GlobalExpansionResult;
  createdAt: string;
}
