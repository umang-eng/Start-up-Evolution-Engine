"""Agent Mesh — Stage configuration with feature flags.

Each stage gets an enabled flag (defaulting to False) so the worker can
route to old BaseModule or new AgentModule per stage without a code deploy.
"""

from backend.agents.types import AgentRole, AgentBudget, StageAgentConfig


AGENT_MESH_CONFIG: dict[str, StageAgentConfig] = {
    "dna": StageAgentConfig(
        enabled=False,
        workflow="sequential",
        agents=[
            AgentRole.RESEARCHER,
            AgentRole.ANALYST,
            AgentRole.SYNTHESIZER,
            AgentRole.REVIEWER,
        ],
        enable_web_research=True,
        budgets={
            AgentRole.RESEARCHER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=3),
            AgentRole.ANALYST: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=2),
            AgentRole.SYNTHESIZER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=0),
            AgentRole.REVIEWER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=0),
        },
    ),
    "features": StageAgentConfig(
        enabled=False,
        workflow="sequential",
        agents=[
            AgentRole.RESEARCHER,
            AgentRole.ANALYST,
            AgentRole.SYNTHESIZER,
        ],
        enable_web_research=True,
        budgets={
            AgentRole.RESEARCHER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=3),
            AgentRole.ANALYST: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=2),
            AgentRole.SYNTHESIZER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=0),
        },
    ),
    "roadmap": StageAgentConfig(
        enabled=False,
        workflow="sequential",
        agents=[
            AgentRole.ANALYST,
            AgentRole.SYNTHESIZER,
            AgentRole.REVIEWER,
        ],
        enable_web_research=False,
        budgets={
            AgentRole.ANALYST: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=2),
            AgentRole.SYNTHESIZER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=0),
            AgentRole.REVIEWER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=0),
        },
    ),
    "team": StageAgentConfig(
        enabled=False,
        workflow="sequential",
        agents=[
            AgentRole.ANALYST,
            AgentRole.SYNTHESIZER,
        ],
        enable_web_research=False,
        budgets={
            AgentRole.ANALYST: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=2),
            AgentRole.SYNTHESIZER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=0),
        },
    ),
    "swot": StageAgentConfig(
        enabled=False,
        workflow="debate",
        agents=[
            AgentRole.RESEARCHER,
            AgentRole.SYNTHESIZER,
            AgentRole.REVIEWER,
        ],
        max_debate_rounds=2,
        enable_web_research=True,
        budgets={
            AgentRole.RESEARCHER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=4),
            AgentRole.SYNTHESIZER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=0),
            AgentRole.REVIEWER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=0),
        },
    ),
    "cost": StageAgentConfig(
        enabled=False,
        workflow="sequential",
        agents=[
            AgentRole.RESEARCHER,
            AgentRole.ANALYST,
            AgentRole.SYNTHESIZER,
        ],
        enable_web_research=True,
        budgets={
            AgentRole.RESEARCHER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=4),
            AgentRole.ANALYST: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=2),
            AgentRole.SYNTHESIZER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=0),
        },
    ),
    "blueprint": StageAgentConfig(
        enabled=False,
        workflow="sequential",
        agents=[
            AgentRole.SYNTHESIZER,
            AgentRole.REVIEWER,
        ],
        enable_web_research=False,
        budgets={
            AgentRole.SYNTHESIZER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=0),
            AgentRole.REVIEWER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=0),
        },
    ),
    "legal_compliance": StageAgentConfig(
        enabled=False,
        workflow="sequential",
        agents=[
            AgentRole.RESEARCHER,
            AgentRole.SYNTHESIZER,
        ],
        enable_web_research=True,
        budgets={
            AgentRole.RESEARCHER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=4),
            AgentRole.SYNTHESIZER: AgentBudget(max_tokens=4000, timeout_s=30, max_tool_calls=0),
        },
    ),
}
