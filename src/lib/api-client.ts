// Frontend HTTP client and backend response adapter layer

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  const isAuthPath = path.startsWith('/api/v1/auth/');

  if (response.status === 401 && !isAuthPath) {
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
  return {
    category: data.category || 'B2B SaaS',
    industry: data.market_type || 'Tech',
    businessModel: data.business_model || '',
    targetMarket: data.customer_type || '',
    valueProposition: data.value_proposition || '',
    usp: data.usp || '',
    summary: data.executive_summary || '',
    scores: {
      innovation: data.scores?.innovation ?? 80,
      scalability: data.scores?.scalability ?? 80,
      complexity: data.scores?.complexity ?? 50,
      opportunity: data.scores?.market_opportunity ?? 80,
      risk: data.scores?.risk_factor ?? 40,
      competition: data.scores?.competition ?? 60,
    },
    recommendations: data.strategic_recommendations || [],
    confidence: Math.round((data.confidence_score ?? 0.8) * 100),
    assumptions: [data.confidence_rationale || 'Context-driven score calculation.'],
    nextSteps: data.strategic_recommendations || [],
  };
}

export function mapFeaturesResponse(data: any): any {
  if (!data) return null;
  const features = (data.features || []).map((f: any) => ({
    id: f.id,
    name: f.name,
    description: f.description,
    category: mapFeatureCategory(f.category),
    priority: mapFeaturePriority(f.priority),
    complexity: (f.complexity || 'MEDIUM').toLowerCase(),
    dependencies: f.dependencies || [],
    benefits: 'Core MVP value capability.',
    risks: 'Complexity dependency risk.',
  }));

  const mvpFeatureIds = (data.features || [])
    .filter((f: any) => f.priority === 'MUST_HAVE')
    .map((f: any) => f.id);

  return {
    totalFeatures: features.length,
    complexityScore: (data.complexityScore || 'medium').toLowerCase(),
    features,
    mvpFeatureIds,
    aiRecommendations: [
      data.mvp_scope_rationale,
      ...(data.core_stack || []).map((tech: string) => `Tech Option: ${tech}`),
      ...(data.blockers || []).map((block: string) => `Risk Blocker: ${block}`),
    ].filter(Boolean),
  };
}

function mapFeatureCategory(category: string): string {
  const cat = (category || 'CORE').toUpperCase();
  if (cat === 'CORE') return 'core';
  if (cat === 'ADVANCED') return 'ai';
  if (cat === 'FUTURE') return 'growth';
  if (cat === 'COMPETITIVE') return 'analytics';
  if (cat === 'GROWTH') return 'growth';
  return 'misc';
}

function mapFeaturePriority(priority: string): string {
  const p = (priority || 'SHOULD_HAVE').toUpperCase();
  if (p === 'MUST_HAVE') return 'critical';
  if (p === 'SHOULD_HAVE') return 'high';
  if (p === 'COULD_HAVE') return 'medium';
  if (p === 'WONT_HAVE') return 'optional';
  return 'medium';
}

export function mapRoadmapResponse(data: any): any {
  if (!data) return null;
  let currentWeek = 1;
  const phases = (data.phases || []).map((p: any, index: number) => {
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
      deliverables: p.milestones || [],
      milestones: p.milestones || [],
      tasks: (p.tasks || []).map((t: any) => ({
        id: t.id,
        name: t.title || t.name,
        durationWeeks: t.duration_weeks ?? 2,
        dependencies: t.dependencies || [],
      })),
      kpis: [`Complete Phase ${index + 1} targets.`],
    };
  });

  return {
    totalDurationWeeks: currentWeek - 1,
    readinessScore: data.launch_readiness_plan?.readiness_score ?? 80,
    phases,
    growthStrategy: data.launch_readiness_plan?.checklist || [],
    recommendations: data.launch_readiness_plan?.checklist || [],
  };
}

export function mapTeamResponse(data: any): any {
  if (!data) return null;
  const roles = (data.org_chart || []).map((r: any) => ({
    id: r.role_id,
    name: r.title,
    department: (r.department || 'Engineering').toLowerCase().replace(' & ', '_').replace(' ', '_'),
    importance: r.hiring_stage === 'Immediate' ? 'critical' : 'high',
    hiringStage: (r.hiring_stage || 'pre-mvp').toLowerCase(),
    responsibilities: r.responsibilities || [],
    skills: r.required_skills || [],
    monthlyCost: Math.round(r.estimated_salary_usd / 12),
    dependencies: r.reports_to ? [r.reports_to] : [],
  }));

  const raci: Record<string, Record<string, string>> = {};
  (data.raci_matrix || []).forEach((entry: any) => {
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
    riskAnalysis: data.hiring_sequence || [],
    recommendations: data.hiring_sequence || [],
  };
}

export function mapSwotResponse(data: any): any {
  if (!data) return null;
  const items: any[] = [];
  
  (data.strengths || []).forEach((s: string, i: number) => {
    items.push({ id: `s_${i}`, type: 'strength', content: s, priority: 'high', urgency: 'high' });
  });
  (data.weaknesses || []).forEach((w: string, i: number) => {
    items.push({ id: `w_${i}`, type: 'weakness', content: w, priority: 'high', urgency: 'high' });
  });
  (data.opportunities || []).forEach((o: string, i: number) => {
    items.push({ id: `o_${i}`, type: 'opportunity', content: o, priority: 'high', urgency: 'high' });
  });
  (data.threats || []).forEach((t: string, i: number) => {
    items.push({ id: `t_${i}`, type: 'threat', content: t, priority: 'high', urgency: 'high' });
  });

  const riskMatrix = (data.mitigations || []).map((m: any, i: number) => ({
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

  (data.founder_actions || []).forEach((fa: any) => {
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
    recommendations: (data.founder_actions || []).map((a: any) => a.action),
    actionPlan,
  };
}

export function mapCostResponse(data: any): any {
  if (!data) return null;
  const costItems = (data.operational_costs || []).map((c: any) => ({
    name: c.description,
    amount: c.monthly_usd,
    category: mapCostCategory(c.category),
    frequency: 'monthly',
  }));

  const scenarios = (data.budget_scenarios || []).map((s: any) => ({
    id: s.name.toLowerCase(),
    name: s.name,
    mvpCost: Math.round(s.monthly_burn_usd * s.runway_months * 0.7),
    year1Cost: Math.round(s.monthly_burn_usd * 12),
    monthlyBurn: s.monthly_burn_usd,
    runwayMonths: s.runway_months,
    description: s.description,
  }));

  return {
    mvpCost: data.mvp_cost_estimate,
    launchCost: Math.round(data.year_1_cost_estimate / 2),
    year1Cost: data.year_1_cost_estimate,
    fundingRequirement: data.funding_requirements?.optimal_target_usd ?? data.mvp_cost_estimate * 1.5,
    riskLevel: (data.financial_risk_level || 'MEDIUM').toLowerCase(),
    readinessRating: 80,
    costItems,
    scenarios,
    recommendations: [data.funding_requirements?.funding_suitability].filter(Boolean),
  };
}

function mapCostCategory(cat: string): string {
  const c = (cat || '').toUpperCase();
  if (c === 'SALARIES') return 'team';
  if (c === 'INFRASTRUCTURE') return 'infrastructure';
  if (c === 'LEGAL_REGISTRATION') return 'legal';
  if (c === 'MARKETING') return 'marketing';
  if (c === 'SAAS_TOOLS') return 'development';
  return 'misc';
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
    run: (projectId: string) => request(`/api/v1/generator/run?project_id=${projectId}`, { method: 'POST' }),
  },
  blueprints: {
    get: (projectId: string) => request(`/api/v1/blueprints/${projectId}`),
    getShared: (token: string) => request(`/api/v1/blueprints/shared/${token}`),
  },
  exports: {
    pdf: (projectId: string) => `${API_BASE_URL}/api/v1/exports/pdf/${projectId}?token=${getAccessToken()}`,
    deck: (projectId: string) => `${API_BASE_URL}/api/v1/exports/deck/${projectId}?token=${getAccessToken()}`,
    share: (projectId: string) => request(`/api/v1/exports/share-link/${projectId}`, { method: 'POST' }),
  },
};
