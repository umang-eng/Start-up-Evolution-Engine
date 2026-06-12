import { StartupDNA, FeatureExtraction, ExecutionRoadmap, OrgStructure, SWOTAnalysis, CostEstimation } from '@/types/blueprint';

export function generateMockDNA(prompt: string): StartupDNA {
  return {
    category: 'AI Platform & B2B SaaS',
    industry: 'Business Tech',
    businessModel: 'Subscription & Usage-based API pricing',
    targetMarket: 'Enterprise teams & Mid-market founders',
    valueProposition: 'Automating operational startup structuring and investor reporting using specialized LLM agents.',
    usp: 'End-to-end cascading context tracking that automatically links financial budgets to feature requirements.',
    summary: `The startup based on "${prompt}" addresses a critical market bottleneck in the venture-backed ecosystem: structural execution friction. By deploying specialized agents to co-author and sync documents, it reduces the launch-planning cycle from weeks to minutes.`,
    scores: {
      innovation: 85,
      scalability: 92,
      complexity: 65,
      opportunity: 88,
      risk: 42,
      competition: 55
    },
    recommendations: [
      "Validate user interest with a low-fidelity landing page detailing cost estimation widgets first.",
      "Build deep integrations with existing database formats to avoid migration friction.",
      "Focus product marketing on 'runway calculations' to capture pre-seed founder attention immediately."
    ],
    confidence: 94,
    assumptions: [
      "Founders are willing to share high-level business ideas with AI planning models.",
      "Regulatory compliance for startup data storage allows client-side caching of strategy documents."
    ],
    nextSteps: [
      "Run 15 targeted founder interviews to map key spreadsheet configurations.",
      "Draft standard developer API interface schemas."
    ]
  };
}

export function generateMockFeatures(prompt: string): FeatureExtraction {
  return {
    totalFeatures: 24,
    complexityScore: 'medium',
    features: [
      {
        id: 'f1',
        name: 'AI Co-Founder Input Canvas',
        description: 'Multi-line text input with auto-enhancements and template suggestions.',
        category: 'core',
        priority: 'critical',
        complexity: 'low',
        dependencies: [],
        benefits: 'Reduces prompt input friction and structures startup descriptions.',
        risks: 'None.'
      },
      {
        id: 'f2',
        name: 'Dynamic Radar Score Chart',
        description: 'SVG-based radial visualization displaying 6 core DNA vectors.',
        category: 'core',
        priority: 'critical',
        complexity: 'low',
        dependencies: [],
        benefits: 'Provides an immediate viability assessment in under 60 seconds.',
        risks: 'None.'
      },
      {
        id: 'f3',
        name: 'React Flow Dependency network',
        description: 'Interactive system layout mapping feature relationships and blockers.',
        category: 'core',
        priority: 'high',
        complexity: 'medium',
        dependencies: ['f1'],
        benefits: 'Helps engineers identify critical path development requirements.',
        risks: 'Complexity of node placement algorithms.'
      },
      {
        id: 'f4',
        name: 'Secured Web Share Link',
        description: 'Generates secure, read-only dashboard links with password control.',
        category: 'growth',
        priority: 'medium',
        complexity: 'medium',
        dependencies: ['f2'],
        benefits: 'Drives viral loops as founders share plans with investors.',
        risks: 'None.'
      },
      {
        id: 'f5',
        name: 'Runway Simulation Sliders',
        description: 'Sliders to simulate burn rates by shifting hiring dates and SaaS spend.',
        category: 'payments',
        priority: 'high',
        complexity: 'medium',
        dependencies: [],
        benefits: 'Builds founder trust by showing cash flow impacts interactively.',
        risks: 'Requires high accuracy in financial formulas.'
      }
    ],
    mvpFeatureIds: ['f1', 'f2', 'f3', 'f5'],
    aiRecommendations: [
      "Postpone custom user authentication systems. Use OAuth integration to save 12 days.",
      "Use serverless database layers to minimize initial cloud hosting overhead."
    ]
  };
}

export function generateMockRoadmap(prompt: string): ExecutionRoadmap {
  return {
    totalDurationWeeks: 18,
    readinessScore: 82,
    phases: [
      {
        id: 'p1',
        name: 'Research & Validation',
        durationWeeks: 2,
        startWeek: 1,
        endWeek: 2,
        deliverables: ['Target Founder Interviews Report', 'Viability Score Matrix'],
        milestones: ['Core Concept Validated'],
        tasks: [
          { id: 't1_1', name: 'Conduct 15 founder discovery interviews', durationWeeks: 1, dependencies: [] },
          { id: 't1_2', name: 'Analyze direct SaaS competitor features', durationWeeks: 1, dependencies: [] }
        ],
        kpis: ['Minimum 85% validation rate from interviews']
      },
      {
        id: 'p2',
        name: 'MVP Development',
        durationWeeks: 8,
        startWeek: 5,
        endWeek: 12,
        deliverables: ['Database Schema specs', 'React Flow layout integration', 'Stripe checkout flow'],
        milestones: ['Working Beta Access Ready'],
        tasks: [
          { id: 't2_1', name: 'Setup database tables and caching layers', durationWeeks: 2, dependencies: [] },
          { id: 't2_2', name: 'Build radar charts and timeline dashboards', durationWeeks: 4, dependencies: ['t2_1'] },
          { id: 't2_3', name: 'Integrate Stripe subscriptions checkout', durationWeeks: 2, dependencies: [] }
        ],
        kpis: ['Page loading speed under 1.5s', 'Test suite coverage above 80%']
      },
      {
        id: 'p3',
        name: 'Launch & Expansion',
        durationWeeks: 4,
        startWeek: 13,
        endWeek: 16,
        deliverables: ['Public launch assets', 'Secure share links dashboard'],
        milestones: ['Product Hunt launch completed'],
        tasks: [
          { id: 't3_1', name: 'Generate landing page marketing copies', durationWeeks: 1, dependencies: [] },
          { id: 't3_2', name: 'Run beta test onboarding with 100 users', durationWeeks: 3, dependencies: [] }
        ],
        kpis: ['Acquire 100 active beta testers', 'User feedback rating above 4.5/5']
      }
    ],
    growthStrategy: [
      "Drive acquisition by offering free, shareable summary widgets to online community channels.",
      "Build integration plugins for popular workspace channels (Notion, Slack) in Phase 4."
    ],
    recommendations: [
      "Ensure early data security protocols. Founders are sensitive about leakages of strategy notes."
    ]
  };
}

export function generateMockTeam(prompt: string): OrgStructure {
  return {
    recommendedTeamSize: 4,
    roles: [
      {
        id: 'r1',
        name: 'Founder / CEO (Product Lead)',
        department: 'product',
        importance: 'critical',
        hiringStage: 'immediate',
        responsibilities: ['Core strategy setting', 'User discovery interviews', 'Investor relationship management'],
        skills: ['Business modeling', 'Product discovery', 'Agile layouts'],
        monthlyCost: 4000,
        dependencies: []
      },
      {
        id: 'r2',
        name: 'Technical Co-Founder (CTO)',
        department: 'engineering',
        importance: 'critical',
        hiringStage: 'immediate',
        responsibilities: ['Main system database modeling', 'API integration', 'AI agent pipeline structures'],
        skills: ['Next.js App Router', 'React Flow', 'Vercel AI SDK', 'PostgreSQL'],
        monthlyCost: 6000,
        dependencies: ['r1']
      },
      {
        id: 'r3',
        name: 'UI/UX Product Designer (Contractor)',
        department: 'design',
        importance: 'high',
        hiringStage: 'pre-mvp',
        responsibilities: ['Mock UI designs', 'Design tokens', 'Micro-interactions configurations'],
        skills: ['Apple HIG guidelines', 'Figma Squircles spacing', 'Tailwind CSS layouts'],
        monthlyCost: 3500,
        dependencies: ['r1']
      },
      {
        id: 'r4',
        name: 'Growth Marketing Lead (Part-Time)',
        department: 'marketing',
        importance: 'medium',
        hiringStage: 'pre-launch',
        responsibilities: ['Landing page validation', 'Viral loop designs', 'Customer acquisition'],
        skills: ['Ad campaigns', 'Product Hunt launch models', 'Copywriting'],
        monthlyCost: 2000,
        dependencies: ['r1']
      }
    ],
    raciMatrix: {
      'r1': {
        'Idea Verification': 'A',
        'System Coding': 'I',
        'Design System': 'C',
        'Launch Marketing': 'A'
      },
      'r2': {
        'Idea Verification': 'C',
        'System Coding': 'R',
        'Design System': 'I',
        'Launch Marketing': 'I'
      },
      'r3': {
        'Idea Verification': 'I',
        'System Coding': 'C',
        'Design System': 'R',
        'Launch Marketing': 'I'
      },
      'r4': {
        'Idea Verification': 'I',
        'System Coding': 'I',
        'Design System': 'I',
        'Launch Marketing': 'R'
      }
    },
    riskAnalysis: [
      "High dependency on Technical Co-Founder. Single point of execution failure if code is delayed.",
      "Lack of support roles (e.g. Quality Assurance testing) increases development bug leakage risks."
    ],
    recommendations: [
      "Use open-source boilerplate structures during Phase 1 to offset early design hiring constraints."
    ]
  };
}

export function generateMockSWOT(prompt: string): SWOTAnalysis {
  return {
    healthScore: 84,
    growthPotential: 88,
    items: [
      { id: 's1', type: 'strength', content: 'Proprietary context alignment algorithms linking text prompts to costs.', priority: 'high', urgency: 'high' },
      { id: 's2', type: 'strength', content: 'Low database infrastructure hosting overhead using serverless templates.', priority: 'medium', urgency: 'medium' },
      { id: 'w1', type: 'weakness', content: 'Small initial pre-seed development runway (estimated 6 months).', priority: 'high', urgency: 'high' },
      { id: 'w2', type: 'weakness', content: 'High founder burnout risk managing product requirements and investor sales.', priority: 'medium', urgency: 'high' },
      { id: 'o1', type: 'opportunity', content: 'Unserved market niches of pre-seed incubator hubs seeking automated spec tools.', priority: 'high', urgency: 'high' },
      { id: 'o2', type: 'opportunity', content: 'Viral growth loops via read-only shareable links viewed by angel investors.', priority: 'medium', urgency: 'medium' },
      { id: 't1', type: 'threat', content: 'Rapid competitive AI feature additions by massive legacy planning platforms.', priority: 'high', urgency: 'high' },
      { id: 't2', type: 'threat', content: 'Data security compliance updates restricting AI parsing of strategic plans.', priority: 'medium', urgency: 'medium' }
    ],
    riskMatrix: [
      {
        threatId: 't1',
        probability: 'high',
        impact: 'high',
        mitigation: 'Build deep user workflow integrations (e.g. Jira syncing) to establish strong platform stickiness.'
      },
      {
        threatId: 't2',
        probability: 'medium',
        impact: 'high',
        mitigation: 'Implement local IndexedDB client-side data storage options, keeping core strategic details private.'
      }
    ],
    opportunityMatrix: [
      { opportunityId: 'o1', impact: 'high', easeOfExecution: 'high' },
      { opportunityId: 'o2', impact: 'medium', easeOfExecution: 'high' }
    ],
    recommendations: [
      "Prioritize sharing features. Virality is the lowest-cost customer acquisition engine for founder tools."
    ],
    actionPlan: {
      immediate: ["Secure domains and setup landing email capture page.", "Set up client databases."],
      days30: ["Conduct first pilot tests with 10 pre-seed startup founders.", "Integrate radar metric dashboards."],
      days60: ["Draft the PRD features schema models.", "Refine cost simulator algorithms."],
      days90: ["Finalize MVP and launch on Product Hunt.", "Start angel funding conversations."]
    }
  };
}

export function generateMockCost(prompt: string): CostEstimation {
  return {
    mvpCost: 15500,
    launchCost: 2000,
    year1Cost: 135000,
    fundingRequirement: 80000,
    riskLevel: 'low',
    readinessRating: 85,
    costItems: [
      { name: 'Technical Co-Founder (First 2 Months)', amount: 12000, category: 'team', frequency: 'one-time' },
      { name: 'UI/UX Designer Contract (MVP UI)', amount: 3500, category: 'team', frequency: 'one-time' },
      { name: 'Vercel Serverless Hosting & DBs', amount: 50, category: 'infrastructure', frequency: 'monthly' },
      { name: 'AI API Endpoint Usage fees', amount: 200, category: 'infrastructure', frequency: 'monthly' },
      { name: 'Product Hunt Launch & Ads Campaign', amount: 1000, category: 'marketing', frequency: 'one-time' },
      { name: 'Stripe Processing fees', amount: 300, category: 'ops', frequency: 'monthly' },
      { name: 'Incorporation & Legal documents', amount: 1000, category: 'legal', frequency: 'one-time' }
    ],
    scenarios: [
      {
        id: 'lean',
        name: 'Lean Startup (Bootstrapped)',
        mvpCost: 15500,
        year1Cost: 85000,
        monthlyBurn: 4500,
        runwayMonths: 6,
        description: 'Focuses entirely on MVP, outsourcing UI and hosting on free/low tiers. Hires delayed.'
      },
      {
        id: 'balanced',
        name: 'Balanced Startup Model',
        mvpCost: 35000,
        year1Cost: 135000,
        monthlyBurn: 11250,
        runwayMonths: 12,
        description: 'Includes full-time tech leads, optimized server layers, and dedicated customer validation.'
      },
      {
        id: 'aggressive',
        name: 'Aggressive Growth Startup',
        mvpCost: 75000,
        year1Cost: 320000,
        monthlyBurn: 26600,
        runwayMonths: 18,
        description: 'Requires pre-seed capital, fast acquisition channels, and dedicated support teams.'
      }
    ],
    recommendations: [
      "Select serverless data structures to keep monthly infrastructure hosting below $100 until beta traction.",
      "Use online incorporation packages to minimize legal overhead bills during the first 30 days."
    ]
  };
}
