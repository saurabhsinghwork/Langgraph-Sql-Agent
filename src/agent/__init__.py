"""Agent package for LangGraph SQL Agents (MCA and GST)."""

# [Project-Defined Imports from src.agent.models]: Structured outcome dataclass and status enum
from src.agent.models import AgentResult, AgentStatus
# [Project-Defined Imports from src.agent.prompts]: System instruction prompts
from src.agent.prompts import (
    AGENT_SYSTEM_PROMPT,
    MCA_AGENT_SYSTEM_PROMPT,
    GST_AGENT_SYSTEM_PROMPT,
    get_prompt_for_agent,
)
# [Project-Defined Imports from src.agent.graph]: Graph builders and agent execution runners
from src.agent.graph import (
    build_agent_graph,
    run_agent,
    run_mca_agent,
    run_gst_agent,
)

# [Built-in Python: __all__]: Public interface exports exposed by the agent package
__all__ = [
    "AgentResult",
    "AgentStatus",
    "AGENT_SYSTEM_PROMPT",
    "MCA_AGENT_SYSTEM_PROMPT",
    "GST_AGENT_SYSTEM_PROMPT",
    "get_prompt_for_agent",
    "build_agent_graph",
    "run_agent",
    "run_mca_agent",
    "run_gst_agent",
]
