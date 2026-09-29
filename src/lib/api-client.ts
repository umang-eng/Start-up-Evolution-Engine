// Frontend HTTP client and backend response adapter layer

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const toArray = (value: any): any[] => {
  if (Array.isArray(value)) return value.filter((item) => item != null);
  return value == null ? [] : [value];
};

const toStringValue = (value: any, fallback = ''): string => {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return fallback;
};

class ApiError extends Error {
  status: number;
  code?: string;
  details?: any;

  constructor(message: string, status: number, code?: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// Token storage helpers
export const getAccessToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
};

export const getRefreshToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('refresh_token');
};

export const setTokens = (access: string, refresh: string) => {
  if (typeof window === 'undefined') return;
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
};

export const clearTokens = () => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};

// Base request wrapper
async function request(path: string, options: RequestInit = {}): Promise<any> {
  const url = `${API_BASE_URL}${path}`;
  const headers = new Headers(options.headers || {});

  // Inject JWT Bearer Token
  const token = getAccessToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, { ...options, headers });

  // Auth endpoints (login, register, refresh) must never trigger the token-refresh
  // loop — a 401 from them is a real credential error, not an expired session.
  const isAuthActionPath = path === '/api/v1/auth/login' || path === '/api/v1/auth/register' || path === '/api/v1/auth/refresh';

  if (response.status === 401 && !isAuthActionPath) {
    // Attempt Token Rotation for protected endpoints
    const refreshed = await attemptTokenRefresh();
    if (refreshed) {
      // Retry with new access token
      headers.set('Authorization', `Bearer ${getAccessToken()}`);
      const retryResponse = await fetch(url, { ...options, headers });
      return handleResponse(retryResponse);
    } else {
      clearTokens();
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      throw new ApiError('Session expired. Please log in again.', 401, 'UNAUTHORIZED');
    }
  }

  return handleResponse(response);
}

async function handleResponse(response: Response): Promise<any> {
  const isJson = response.headers.get('content-type')?.includes('application/json');
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const errorMsg = payload.error?.message || payload.detail || response.statusText || 'An error occurred';
    throw new ApiError(
      errorMsg,
      response.status,
      payload.error?.code || 'API_ERROR',
      payload.error?.details
    );
  }

  return payload.data ?? payload;
}

// Token rotation helper
async function attemptTokenRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh?refresh_token=${encodeURIComponent(refresh)}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (response.ok) {
      const payload = await response.json();
      if (payload.success && payload.data) {
        setTokens(payload.data.access_token, payload.data.refresh_token);
        return true;
      }
    }
  } catch (err) {
    console.error('Failed to rotate session tokens:', err);
  }
  return false;
}

// BACKEND DATA SCHEMAS MAPPING ADAPTERS

export function mapDnaResponse(data: any): any {
  if (!data) return null;
  const scores = data.scores || {};
  return {
    category: data.category || 'B2B SaaS',
    industry: data.market_type || data.industry || 'Tech',
    businessModel: data.business_model || data.businessModel || '',
    targetMarket: data.customer_type || data.targetMarket || '',
    valueProposition: data.value_proposition || data.valueProposition || '',
    usp: data.usp || '',
    summary: data.executive_summary || data.summary || '',
    scores: {
      innovation: scores.innovation ?? 80,
      scalability: scores.scalability ?? 80,
      complexity: scores.complexity ?? 50,
      opportunity: scores.market_opportunity ?? scores.opportunity ?? 80,
      risk: scores.risk_factor ?? scores.risk ?? 40,
      competition: scores.competition ?? 60,
    },
    recommendations: toArray(data.strategic_recommendations || data.recommendations),
    confidence: Math.round(((data.confidence_score ?? data.confidence ?? 0.8)) * (data.confidence_score !== undefined && data.confidence_score <= 1 ? 100 : 1)),
    assumptions: [data.confidence_rationale || 'Context-driven score calculation.'],
    nextSteps: toArray(data.strategic_recommendations || data.nextSteps),
  };
}

export function mapFeaturesResponse(data: any): any {
  if (!data) return null;
  const sourceFeatures = toArray(data.features);
  const features = sourceFeatures.map((f: any, idx: number) => ({
    id: f.id || `feature_${idx}`,
    name: f.name || 'Unnamed Feature',
    description: f.description || '',
    category: mapFeatureCategory(f.category),
    priority: mapFeaturePriority(f.priority),
    complexity: toStringValue(f.complexity, 'MEDIUM').toLowerCase(),
    dependencies: toArray(f.dependencies),
    benefits: f.benefits || 'Core MVP value capability.',
    risks: f.risks || 'Complexity dependency risk.',
  }));

  const mvpFeatureIds = sourceFeatures
    .filter((f: any) => f.priority === 'MUST_HAVE' || f.priority === 'critical')
    .map((f: any, idx: number) => f.id || `feature_${idx}`);

  // Derive complexity score from the actual feature items since backend has no top-level field
  const complexityCounts = features.reduce((acc: Record<string, number>, f: any) => {
    const c = toStringValue(f.complexity, 'medium').toLowerCase();
    acc[c] = (acc[c] || 0) + 1;
    return acc;
  }, {});
  const dominantComplexity = Object.entries(complexityCounts)
    .sort(([, a], [, b]) => (b as number) - (a as number))[0]?.[0] || 'medium';
  // Also accept explicit field from backend if ever added
  const complexityRaw = data.complexity_score || data.complexityScore || dominantComplexity;

  return {
    totalFeatures: features.length,
    complexityScore: String(complexityRaw).toLowerCase(),
    features,
    mvpFeatureIds,
    aiRecommendations: [
      data.mvp_scope_rationale,
      ...toArray(data.core_stack).map((tech: string) => `Recommended Stack: ${tech}`),
      ...toArray(data.blockers).map((block: string) => `Risk Blocker: ${block}`),
    ].filter(Boolean),
  };
}

function mapFeatureCategory(category: any): string {
  const cat = toStringValue(category, 'CORE').toUpperCase();
  if (cat === 'CORE') return 'core';
  if (cat === 'ADVANCED') return 'ai';
  if (cat === 'FUTURE') return 'growth';
  if (cat === 'COMPETITIVE') return 'analytics';
  if (cat === 'GROWTH') return 'growth';
  return 'misc';
}

function mapFeaturePriority(priority: any): string {
  const p = toStringValue(priority, 'SHOULD_HAVE').toUpperCase();
  if (p === 'MUST_HAVE') return 'critical';
  if (p === 'SHOULD_HAVE') return 'high';
  if (p === 'COULD_HAVE') return 'medium';
  if (p === 'WONT_HAVE') return 'optional';
  return 'medium';
}

export function mapRoadmapResponse(data: any): any {
  if (!data) return null;
  let currentWeek = 1;
  const phases = toArray(data.phases).map((p: any, index: number) => {
    const durationWeeks = (p.duration_months || 1) * 4;
    const startWeek = currentWeek;
    const endWeek = currentWeek + durationWeeks - 1;
    currentWeek += durationWeeks;

    return {
      id: p.phase_id || `phase_${index}`,
      name: p.name || 'Development Phase',
      durationWeeks,
      startWeek,
      endWeek,
      deliverables: toArray(p.milestones),
      milestones: toArray(p.milestones),
      tasks: toArray(p.tasks).map((t: any) => ({
        id: t.id,
        name: t.title || t.name,
        durationWeeks: t.duration_weeks ?? 2,
        dependencies: toArray(t.dependencies),
      })),
      kpis: [`Complete Phase ${index + 1} targets.`],
    };
  });

  return {
    totalDurationWeeks: currentWeek - 1,
    readinessScore: data.launch_readiness_plan?.readiness_score ?? 80,
    phases,
    growthStrategy: toArray(data.launch_readiness_plan?.checklist),
    recommendations: toArray(data.launch_readiness_plan?.checklist),
  };
}

export function mapTeamResponse(data: any): any {
  if (!data) return null;
  const roles = toArray(data.org_chart).map((r: any) => ({
    id: r.role_id,
    name: r.title,
    department: toStringValue(r.department, 'Engineering').toLowerCase().replace(' & ', '_').replace(' ', '_'),
    importance: r.hiring_stage === 'Immediate' ? 'critical' : 'high',
    hiringStage: toStringValue(r.hiring_stage, 'pre-mvp').toLowerCase(),
    responsibilities: toArray(r.responsibilities),
    skills: toArray(r.required_skills),
    monthlyCost: Math.round(r.estimated_salary_usd / 12),
    dependencies: r.reports_to ? [r.reports_to] : [],
  }));

  const raci: Record<string, Record<string, string>> = {};
  toArray(data.raci_matrix).forEach((entry: any) => {
    const taskId = entry.task_id;
    if (entry.responsible_role_id) {
      if (!raci[entry.responsible_role_id]) raci[entry.responsible_role_id] = {};
      raci[entry.responsible_role_id][taskId] = 'R';
    }
    if (entry.accountable_role_id) {
      if (!raci[entry.accountable_role_id]) raci[entry.accountable_role_id] = {};
      raci[entry.accountable_role_id][taskId] = 'A';
    }
  });

  return {
    recommendedTeamSize: data.recommended_team_size || roles.length,
    roles,
    raciMatrix: raci,
    riskAnalysis: toArray(data.hiring_sequence),
    recommendations: toArray(data.hiring_sequence),
  };
}

export function mapSwotResponse(data: any): any {
  if (!data) return null;
  const items: any[] = [];
  
  toArray(data.strengths).forEach((s: string, i: number) => {
    items.push({ id: `s_${i}`, type: 'strength', content: s, priority: 'high', urgency: 'high' });
  });
  toArray(data.weaknesses).forEach((w: string, i: number) => {
    items.push({ id: `w_${i}`, type: 'weakness', content: w, priority: 'high', urgency: 'high' });
  });
  toArray(data.opportunities).forEach((o: string, i: number) => {
    items.push({ id: `o_${i}`, type: 'opportunity', content: o, priority: 'high', urgency: 'high' });
  });
  toArray(data.threats).forEach((t: string, i: number) => {
    items.push({ id: `t_${i}`, type: 'threat', content: t, priority: 'high', urgency: 'high' });
  });

  const riskMatrix = toArray(data.mitigations).map((m: any, i: number) => ({
    threatId: `threat_mit_${i}`,
    probability: m.probability >= 3 ? 'high' : m.probability === 2 ? 'medium' : 'low',
    impact: m.impact >= 3 ? 'high' : m.impact === 2 ? 'medium' : 'low',
    mitigation: `${m.threat_description} -> Mitigate via: ${m.mitigation_strategy}`,
  }));

  const actionPlan = {
    immediate: [] as string[],
    days30: [] as string[],
    days60: [] as string[],
    days90: [] as string[],
  };

  const founderActions = toArray(data.founder_actions);
  founderActions.forEach((fa: any) => {
    if (fa.horizon === 'IMMEDIATE_30_DAYS') actionPlan.immediate.push(fa.action);
    else if (fa.horizon === 'SHORT_TERM_60_DAYS') actionPlan.days30.push(fa.action);
    else if (fa.horizon === 'MEDIUM_TERM_90_DAYS') actionPlan.days60.push(fa.action);
    else actionPlan.days90.push(fa.action);
  });

  return {
    healthScore: 80,
    growthPotential: 85,
    items,
    riskMatrix,
    opportunityMatrix: [],
    recommendations: founderActions.map((a: any) => a.action),
    actionPlan,
  };
}

export function mapCostResponse(data: any): any {
  if (!data) return null;
  const costItems = toArray(data.operational_costs).map((c: any) => ({
    name: c.description || c.name || 'Cost Item',
    amount: c.monthly_usd || c.amount || 0,
    category: mapCostCategory(c.category || ''),
    frequency: 'monthly',
  }));

  const scenarios = toArray(data.budget_scenarios).map((s: any, idx: number) => ({
    id: toStringValue(s.name, `scenario_${idx}`).toLowerCase().replace(/\s+/g, '_'),
    name: s.name || `Scenario ${idx + 1}`,
    mvpCost: Math.round((s.monthly_burn_usd || 0) * (s.runway_months || 12) * 0.7),
    year1Cost: Math.round((s.monthly_burn_usd || 0) * 12),
    monthlyBurn: s.monthly_burn_usd || 0,
    runwayMonths: s.runway_months || 12,
    description: s.description || '',
  }));

  const mvpCost = data.mvp_cost_estimate || data.mvpCost || 0;
  const year1Cost = data.year_1_cost_estimate || data.year1Cost || 0;
  const fundingReq = data.funding_requirements?.optimal_target_usd
    ?? data.fundingRequirement
    ?? (mvpCost * 1.5);

  return {
    mvpCost,
    launchCost: Math.round(year1Cost / 2),
    year1Cost,
    fundingRequirement: fundingReq,
    riskLevel: toStringValue(data.financial_risk_level || data.riskLevel, 'MEDIUM').toLowerCase(),
    readinessRating: 80,
    costItems,
    scenarios,
    recommendations: [data.funding_requirements?.funding_suitability].filter(Boolean),
  };
}

function mapCostCategory(cat: any): string {
  const c = toStringValue(cat).toUpperCase();
  if (c === 'SALARIES') return 'team';
  if (c === 'INFRASTRUCTURE') return 'infrastructure';
  if (c === 'LEGAL_REGISTRATION') return 'legal';
  if (c === 'MARKETING') return 'marketing';
  if (c === 'SAAS_TOOLS') return 'development';
  return 'misc';
}

export function mapLegalComplianceResponse(data: any): any {
  if (!data) return null;
  const checklist = toArray(
    data.compliance_checklist || data.registration_requirements,
  );
  return {
    compliance_checklist: checklist.map((c: any) => ({
      item: c.item || c.name || c.requirement_name || '',
      status: toStringValue(c.status, 'pending').toLowerCase(),
      notes: c.notes || c.description || '',
    })),
    ip_protection: toArray(data.ip_protection || data.data_protection_requirements),
    regulatory_requirements: toArray(data.regulatory_requirements || data.compliance_directories),
    grants_incentives: toArray(data.grants_incentives || data.funding_sources),
    registrations_needed: toArray(data.registrations_needed || data.registration_requirements),
    overall_risk: data.overall_risk || 'medium',
    recommendations: toArray(data.recommendations),
    summary: data.summary || '',
    estimated_compliance_budget_usd: data.estimated_compliance_budget_usd || 0,
  };
}

export function mapCompetitiveMoatResponse(data: any): any {
  if (!data) return null;
  const dimensions = toArray(data.moat_dimensions);
  return {
    competitors: toArray(data.competitor_landscape || data.competitors).map((c: any) => ({
      name: c.name || '',
      strength: c.strength || c.description || '',
      weakness: c.weakness || '',
      threat_level: toStringValue(c.threat_level, 'medium').toLowerCase(),
    })),
    moat_scores: toArray(data.moat_scores || data.scores || dimensions).map((s: any) => ({
      dimension: s.dimension || s.name || s.moat_type || '',
      score: s.score ?? s.strength ?? 0,
      evidence: s.evidence || '',
    })),
    positioning: toArray(data.positioning || data.competitive_position),
    copy_difficulty: toArray(data.copy_difficulty),
    overall_moat_strength: data.overall_moat_strength
      || data.moat_score
      || data.overall_moat_score?.value
      || 50,
    strategic_recommendations: toArray(
      data.strategic_recommendations || data.build_recommendations || data.recommendations,
    ),
  };
}

export function mapStressTestResponse(data: any): any {
  if (!data) return null;
  const normalizeLevel = (value: unknown, numericLabels: string[]): string => {
    if (typeof value === 'string') return value.toLowerCase().replace(/[\s-]+/g, '_');
    if (typeof value === 'number') {
      const index = Math.max(0, Math.min(numericLabels.length - 1, Math.round(value * (numericLabels.length - 1))));
      return numericLabels[index];
    }
    return numericLabels[Math.floor(numericLabels.length / 2)];
  };
  return {
    scenarios: toArray(data.scenarios).map((s: any) => ({
      name: s.name || s.scenario_name || '',
      description: s.description || '',
      probability: normalizeLevel(s.probability, ['low', 'medium', 'high']),
      impact: normalizeLevel(s.impact || s.impact_score, ['negligible', 'minor', 'moderate', 'severe', 'catastrophic']),
      mitigation: s.mitigation || s.mitigation_strategy || '',
      recovery_time: s.recovery_time || s.recovery_plan || s.recovery || '',
    })),
    risk_scores: toArray(data.risk_scores || data.risks).map((r: any) => ({
      risk: r.risk || r.name || '',
      score: r.score || 0,
      probability: normalizeLevel(r.probability, ['low', 'medium', 'high']),
      impact: normalizeLevel(r.impact || r.impact_score, ['negligible', 'minor', 'moderate', 'severe', 'catastrophic']),
    })),
    resilience_score: data.resilience_score || data.resilience || data.overall_resilience?.value || 50,
    critical_dependencies: toArray(data.critical_dependencies),
    recommendations: toArray(data.recommendations || data.resilience_recommendations),
  };
}

export function mapFinancialIntelligenceResponse(data: any): any {
  if (!data) return null;
  const projections = toArray(data.projections || data.financial_projections);
  const economics = data.unit_economics;
  const unitEconomics = Array.isArray(economics)
    ? economics.map((item: any) => ({
        metric: item.metric || item.name || '',
        value: item.value ?? 0,
        benchmark: item.benchmark || '',
      }))
    : economics && typeof economics === 'object'
      ? [
          ['Customer Acquisition Cost', 'cac', 'USD'],
          ['Lifetime Value', 'ltv', 'USD'],
          ['LTV/CAC Ratio', 'ltv_cac_ratio', 'ratio'],
          ['Payback Period', 'payback_period_months', 'months'],
          ['Gross Margin', 'gross_margin_percent', '%'],
          ['Net Margin', 'net_margin_percent', '%'],
          ['Contribution Margin', 'contribution_margin_percent', '%'],
          ['Churn Rate', 'churn_rate_percent', '%'],
          ['Expansion Rate', 'expansion_rate_percent', '%'],
        ]
          .filter(([, key]) => economics[key] != null)
          .map(([metric, key, unit]) => ({
            metric,
            value: economics[key],
            benchmark: unit,
          }))
      : [];
  const funding = data.funding_analysis || data.funding_requirements;
  const valuation = data.valuation_model || data.valuation;
  return {
    projection_format: projections.some((projection: any) => projection.period) ? 'period' : 'monthly',
    projections: projections.map((p: any) => ({
      period: p.period || p.metric || p.name || '',
      metric: p.metric || p.name || p.period || '',
      revenue: p.revenue ?? 0,
      costs: p.costs ?? 0,
      profit: p.profit ?? 0,
      cash_balance: p.cash_balance ?? 0,
      customers: p.customers ?? 0,
      arr: p.arr ?? 0,
      mrr: p.mrr ?? 0,
      month_1: p.month_1 ?? p.m1 ?? 0,
      month_6: p.month_6 ?? p.m6 ?? 0,
      month_12: p.month_12 ?? p.m12 ?? 0,
      month_24: p.month_24 ?? p.m24 ?? 0,
    })),
    unit_economics: unitEconomics,
    funding_analysis: Array.isArray(funding)
      ? funding
      : funding && typeof funding === 'object'
        ? [{
            stage: funding.current_round || funding.stage || '',
            amount: String(funding.amount ?? funding.optimal_target_usd ?? ''),
            timeline: String(funding.timeline ?? ''),
            milestones_needed: toArray(funding.milestones_needed),
          }]
        : [],
    valuation_model: Array.isArray(valuation)
      ? valuation
      : valuation && typeof valuation === 'object'
        ? [{
            method: valuation.method || '',
            estimated_value: String(valuation.estimated_value ?? ''),
            confidence: String(valuation.confidence ?? ''),
          }]
        : [],
    financial_health_score: data.financial_health_score ?? data.health_score ?? 50,
    recommendations: toArray(data.recommendations),
  };
}

export function mapInvestmentCommitteeResponse(data: any): any {
  if (!data) return null;
  const rawRecommendation = data.recommendation ?? data.investment_recommendation;
  const recommendation = rawRecommendation && typeof rawRecommendation === 'object'
    ? rawRecommendation
    : null;
  const recommendationText = (value: any): string => {
    if (typeof value === 'string') return value;
    if (typeof value === 'number') return String(value);
    return '';
  };
  const recommendationLabel = recommendationText(
    typeof data.investment_recommendation === 'string'
      ? data.investment_recommendation
      : recommendation?.recommendation || data.recommendation,
  );
  const thesis = recommendationText(recommendation?.investment_thesis);
  return {
    partner_cards: toArray(data.partner_cards || data.partners || data.committee_members).map((p: any) => ({
      name: p.name || '',
      role: p.role || p.firm || '',
      vote: String(p.vote || 'abstain').toLowerCase().replace('invest', 'approve').replace('pass', 'reject'),
      reasoning: p.reasoning || p.analysis || p.thesis || '',
      concerns: toArray(p.concerns || p.key_concern),
    })),
    investment_recommendation: [recommendationLabel, thesis].filter(Boolean).join(' — '),
    term_sheet: toArray(data.term_sheet).map((term: any, index: number) =>
      typeof term === 'string'
        ? { term: `Term ${index + 1}`, value: term }
        : { term: term.term || term.name || '', value: String(term.value ?? '') },
    ),
    due_diligence: toArray(data.due_diligence || recommendation?.due_diligence_checklist).map((item: any) =>
      typeof item === 'string'
        ? { area: item, status: 'flag', notes: 'Requires validation' }
        : { area: item.area || item.name || '', status: item.status || 'flag', notes: item.notes || item.description || '' },
    ),
    overall_score: data.overall_score || data.score || data.confidence?.score || recommendation?.confidence?.score || 50,
    conditions: toArray(data.conditions || recommendation?.reasons_not_to_invest),
  };
}

export function mapProductExecutionResponse(data: any): any {
  if (!data) return null;
  return {
    prd_summary: data.prd_summary || data.summary || '',
    sprint_plan: toArray(data.sprint_plan || data.sprints).map((s: any) => ({
      sprint: s.sprint || s.number || 0,
      name: s.name || '',
      goals: toArray(s.goals),
      duration_weeks: s.duration_weeks || 2,
    })),
    architecture: toArray(data.architecture).map((a: any) => ({
      component: a.component || a.name || '',
      technology: a.technology || a.tech || '',
      rationale: a.rationale || a.reason || '',
    })),
    api_endpoints: toArray(data.api_endpoints),
    technical_debt: toArray(data.technical_debt),
    launch_readiness: data.launch_readiness || data.readiness_score || 50,
    recommendations: toArray(data.recommendations),
  };
}

export function mapGlobalExpansionResponse(data: any): any {
  if (!data) return null;
  return {
    target_markets: toArray(data.target_markets || data.markets).map((m: any) => ({
      country: m.country || m.name || '',
      market_size: m.market_size || m.size || '',
      growth_rate: m.growth_rate || m.growth || '',
      entry_difficulty: toStringValue(m.entry_difficulty || m.difficulty, 'medium').toLowerCase(),
      priority: toStringValue(m.priority, 'medium').toLowerCase(),
    })),
    expansion_waves: toArray(data.expansion_waves || data.waves),
    localization: toArray(data.localization),
    global_risks: toArray(data.global_risks || data.risks),
    total_addressable_market_global: data.total_addressable_market_global || data.tam_global || '',
    recommendations: toArray(data.recommendations),
  };
}

// API REQUEST ENDPOINTS

export const api = {
  auth: {
    register: (payload: any) => request('/api/v1/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
    login: (payload: any) => request('/api/v1/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
    me: () => request('/api/v1/auth/me'),
  },
  projects: {
    list: () => request('/api/v1/projects'),
    create: (payload: any) => request('/api/v1/projects', { method: 'POST', body: JSON.stringify(payload) }),
    get: (id: string) => request(`/api/v1/projects/${id}`),
    delete: (id: string) => request(`/api/v1/projects/${id}`, { method: 'DELETE' }),
  },
  generator: {
    run: (projectId: string, stage?: string) => request(`/api/v1/generator/run?project_id=${projectId}${stage ? `&stage=${stage}` : ''}`, { method: 'POST' }),
    cancel: (projectId: string) => request(`/api/v1/generator/cancel?project_id=${projectId}`, { method: 'POST' }),
    enhance: (idea: string) => request('/api/v1/generator/enhance', {
      method: 'POST',
      body: JSON.stringify({ idea }),
    }),
  },
  blueprints: {
    get: (projectId: string, allowPartial: boolean = false) => request(`/api/v1/blueprints/${projectId}${allowPartial ? '?allow_partial=true' : ''}`),
    getShared: (token: string) => request(`/api/v1/blueprints/shared/${token}`),
  },
  exports: {
    pdf: (projectId: string) => `${API_BASE_URL}/api/v1/exports/pdf/${projectId}?token=${getAccessToken()}`,
    deck: (projectId: string) => `${API_BASE_URL}/api/v1/exports/deck/${projectId}?token=${getAccessToken()}`,
    share: (projectId: string) => request(`/api/v1/exports/share-link/${projectId}`, { method: 'POST' }),
  },
  intake: {
    start: (rawIdea: string) => request('/api/v1/intake/start', {
      method: 'POST',
      body: JSON.stringify({ raw_idea: rawIdea }),
    }),
    message: (sessionId: string, questionId: string, answer: string) => request('/api/v1/intake/message', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, question_id: questionId, answer }),
    }),
    finalize: (sessionId: string) => request('/api/v1/intake/finalize', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    }),
  },
  meetings: {
    list: (offset = 0, limit = 50) => request(`/api/v1/meetings?offset=${offset}&limit=${limit}`),
    create: (payload: { project_id?: string; title?: string; language?: string }) =>
      request('/api/v1/meetings', { method: 'POST', body: JSON.stringify(payload) }),
    get: (id: string) => request(`/api/v1/meetings/${id}`),
    update: (id: string, payload: any) =>
      request(`/api/v1/meetings/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
    delete: (id: string) => request(`/api/v1/meetings/${id}`, { method: 'DELETE' }),
    uploadTranscript: (meetingId: string, rawText: string, language?: string) =>
      request(`/api/v1/meetings/${meetingId}/transcript`, {
        method: 'POST',
        body: JSON.stringify({ raw_text: rawText, language_detected: language }),
      }),
    uploadSegments: (meetingId: string, segments: any[]) =>
      request(`/api/v1/meetings/${meetingId}/transcript/segments`, {
        method: 'POST',
        body: JSON.stringify({ segments }),
      }),
    getTranscript: (meetingId: string) => request(`/api/v1/meetings/${meetingId}/transcript`),
    uploadAudio: (meetingId: string, audioBlob: Blob, filename: string = 'recording.webm') => {
      const formData = new FormData();
      formData.append('file', audioBlob, filename);
      return request(`/api/v1/meetings/${meetingId}/transcript/audio`, {
        method: 'POST',
        body: formData,
      });
    },
    generateReport: (meetingId: string) =>
      request(`/api/v1/meetings/${meetingId}/report/generate`, { method: 'POST' }),
    getReport: (meetingId: string) => request(`/api/v1/meetings/${meetingId}/report`),
    getHealth: (meetingId: string) => request(`/api/v1/meetings/${meetingId}/health`),
    getTimeline: (meetingId: string) => request(`/api/v1/meetings/${meetingId}/timeline`),
    analyze: (meetingId: string) => request(`/api/v1/meetings/${meetingId}/analyze`, { method: 'POST' }),
  },
};
