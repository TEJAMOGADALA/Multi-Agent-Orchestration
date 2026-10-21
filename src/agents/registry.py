"""Registry that constructs the appropriate thin specialized agent."""

from __future__ import annotations

from typing import Any, ClassVar

from src.agents.base import BaseAgent
from src.config.constants import (
    ANALYSIS_AGENT_SYSTEM_PROMPT,
    CODING_AGENT_SYSTEM_PROMPT,
    RESEARCH_AGENT_SYSTEM_PROMPT,
    AgentType,
)


class ResearchAgent(BaseAgent):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(AgentType.RESEARCH, RESEARCH_AGENT_SYSTEM_PROMPT, **kwargs)


class CodingAgent(BaseAgent):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(AgentType.CODING, CODING_AGENT_SYSTEM_PROMPT, **kwargs)


class AnalysisAgent(BaseAgent):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(AgentType.ANALYSIS, ANALYSIS_AGENT_SYSTEM_PROMPT, **kwargs)


class AgentRegistry:
    _agents: ClassVar[dict[AgentType, type[BaseAgent]]] = {
        AgentType.RESEARCH: ResearchAgent,
        AgentType.CODING: CodingAgent,
        AgentType.ANALYSIS: AnalysisAgent,
    }

    @classmethod
    def create_agent(cls, agent_type: AgentType | str, **kwargs: Any) -> BaseAgent:
        try:
            return cls._agents[AgentType(agent_type)](**kwargs)
        except (KeyError, ValueError) as exc:
            raise ValueError(f"No agent registered for {agent_type!r}") from exc
