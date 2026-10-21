# ============================================================
# DevAgent — Multi-Agent Orchestration System
# src/config/constants.py — Enums, defaults, system-wide constants
# ============================================================
# This module defines all constant values used across DevAgent.
# Nothing here reads from .env — those live in settings.py.
# Constants are immutable, deterministic values known at code time.
#
# Usage:
#   from src.config.constants import AgentType, TaskStatus
#   agent = AgentType.RESEARCH
#   status = TaskStatus.PENDING
# ============================================================

from __future__ import annotations

from enum import Enum, IntEnum, unique


# ==========================================================
# 1. AGENT TYPES — The specialized agents in the system
# ==========================================================
@unique
class AgentType(str, Enum):
    """
    Enumeration of all specialized agents in DevAgent.
    Inherits from str so values serialize cleanly to JSON.

    Usage:
        agent_type = AgentType.RESEARCH
        print(agent_type.value)  # "research"
        print(agent_type.description)  # "Web search and information gathering"
    """

    RESEARCH = "research"
    CODING = "coding"
    ANALYSIS = "analysis"

    @property
    def description(self) -> str:
        """Human-readable description of each agent's role."""
        descriptions: dict[str, str] = {
            "research": "Web search and information gathering",
            "coding": "Code generation, execution, and debugging",
            "analysis": "Data analysis, database queries, and visualization",
        }
        return descriptions[self.value]

    @property
    def default_tools(self) -> list[str]:
        """Default tool names assigned to each agent type."""
        tool_map: dict[str, list[str]] = {
            "research": ["web_search", "web_scrape", "summarize"],
            "coding": ["code_executor", "github", "file_manager"],
            "analysis": ["database_query", "api_caller", "data_visualizer"],
        }
        return tool_map[self.value]


# ==========================================================
# 2. TASK STATUS — Lifecycle states for a task
# ==========================================================
@unique
class TaskStatus(str, Enum):
    """
    Lifecycle states for a user-submitted task.
    Follows a linear progression with branch states for errors.

    Flow:
        PENDING → PLANNING → EXECUTING → VALIDATING → COMPLETED
                                 ↓              ↓
                              FAILED         FAILED
                                 ↓
                             RETRYING → EXECUTING
    """

    PENDING = "pending"          # Task received, queued for processing
    PLANNING = "planning"        # Orchestrator is decomposing into subtasks
    EXECUTING = "executing"      # Agents are working on subtasks
    VALIDATING = "validating"    # Results being cross-validated
    SYNTHESIZING = "synthesizing"  # Combining validated results into response
    COMPLETED = "completed"      # Successfully finished
    FAILED = "failed"            # Failed after all retries exhausted
    RETRYING = "retrying"        # Failed subtask being retried
    CANCELLED = "cancelled"      # Cancelled by user or system
    TIMED_OUT = "timed_out"      # Exceeded ORCHESTRATOR_TIMEOUT

    @property
    def is_terminal(self) -> bool:
        """Check if this is a final state (no further transitions)."""
        return self in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMED_OUT,
        )

    @property
    def is_active(self) -> bool:
        """Check if the task is currently being processed."""
        return self in (
            TaskStatus.PLANNING,
            TaskStatus.EXECUTING,
            TaskStatus.VALIDATING,
            TaskStatus.SYNTHESIZING,
            TaskStatus.RETRYING,
        )


# ==========================================================
# 3. SUBTASK STATUS — Lifecycle states for individual subtasks
# ==========================================================
@unique
class SubTaskStatus(str, Enum):
    """Status of an individual subtask assigned to an agent."""

    PENDING = "pending"          # Waiting for agent assignment
    ASSIGNED = "assigned"        # Agent picked up the subtask
    IN_PROGRESS = "in_progress"  # Agent is actively working
    COMPLETED = "completed"      # Agent finished successfully
    FAILED = "failed"            # Agent failed (may be retried)
    SKIPPED = "skipped"          # Skipped (dependency failed or not needed)


# ==========================================================
# 4. PRIORITY LEVELS — Task urgency ranking
# ==========================================================
@unique
class Priority(IntEnum):
    """
    Task priority levels. Lower number = higher priority.
    Uses IntEnum for natural ordering (Priority.CRITICAL < Priority.LOW).
    """

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

    @property
    def label(self) -> str:
        """Human-readable label with emoji."""
        labels: dict[int, str] = {
            1: "🔴 Critical",
            2: "🟠 High",
            3: "🟡 Medium",
            4: "🟢 Low",
        }
        return labels[self.value]


# ==========================================================
# 5. LLM PROVIDER — Supported LLM providers
# ==========================================================
@unique
class LLMProvider(str, Enum):
    """Supported LLM providers with their LangChain class paths."""

    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"

    @property
    def langchain_class(self) -> str:
        """LangChain chat model class name for this provider."""
        class_map: dict[str, str] = {
            "openai": "langchain_openai.ChatOpenAI",
            "azure_openai": "langchain_openai.AzureChatOpenAI",
            "anthropic": "langchain_anthropic.ChatAnthropic",
            "google": "langchain_google_genai.ChatGoogleGenerativeAI",
        }
        return class_map[self.value]


# ==========================================================
# 6. MCP CONSTANTS — Model Context Protocol defaults
# ==========================================================
@unique
class MCPTransport(str, Enum):
    """Supported MCP transport protocols."""

    STDIO = "stdio"           # Standard I/O (local process)
    SSE = "sse"               # Server-Sent Events (HTTP)
    STREAMABLE_HTTP = "streamable_http"  # Streamable HTTP (newest)


@unique
class MCPToolSource(str, Enum):
    """Identifies where a tool came from — internal or MCP."""

    INTERNAL = "internal"     # Built-in DevAgent tool (Phase 4)
    MCP = "mcp"               # Discovered from an external MCP server


# ==========================================================
# 7. SYSTEM DEFAULTS — Hardcoded defaults (not configurable)
# ==========================================================

# --- API ---
API_V1_PREFIX = "/api/v1"
HEALTH_ENDPOINT = "/health"
READY_ENDPOINT = "/ready"

# --- Task Processing ---
DEFAULT_TASK_PRIORITY = Priority.MEDIUM
MAX_TASK_DESCRIPTION_CHARS = 10000
MAX_SUBTASK_DEPTH = 3          # Prevent recursive subtask decomposition

# --- Agent Behavior ---
AGENT_SYSTEM_PROMPT_MAX_LENGTH = 5000
AGENT_RESPONSE_MAX_LENGTH = 50000
AGENT_TOOL_CALL_MAX_PER_TURN = 10  # Max tool calls an agent can make per turn

# --- Memory & Context ---
CONTEXT_WINDOW_MAX_TOKENS = 128000  # Max context window for shared memory
SHARED_MEMORY_KEY_PREFIX = "devagent:memory:"
SESSION_KEY_PREFIX = "devagent:session:"
RATE_LIMIT_KEY_PREFIX = "devagent:ratelimit:"

# --- MCP ---
MCP_CONFIG_FILENAME = "mcp_config.json"
MCP_TOOL_SCHEMA_VERSION = "1.0"
MCP_MAX_TOOLS_PER_SERVER = 100     # Safety limit on tool discovery

# --- Monitoring ---
METRIC_PREFIX = "devagent_"        # Prometheus metric name prefix

# --- Cost Tracking (USD per 1M tokens, approximate) ---
LLM_COST_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}


# ==========================================================
# 8. SYSTEM PROMPTS — Agent role definitions
# ==========================================================

ORCHESTRATOR_SYSTEM_PROMPT = """You are the DevAgent Orchestrator, a task planning AI.
Your job is to decompose complex user queries into clear, actionable subtasks
and assign each subtask to the most appropriate specialized agent.

Available agents:
- RESEARCH: Web search, information gathering, fact-checking
- CODING: Code generation, debugging, execution, GitHub operations
- ANALYSIS: Data analysis, database queries, API calls, visualization

Rules:
1. Break tasks into the minimum number of subtasks needed.
2. Identify dependencies between subtasks (which must complete before others).
3. Assign each subtask to exactly one agent type.
4. Be specific in subtask descriptions — agents work independently.
5. Never create more than {max_subtasks} subtasks.
"""

RESEARCH_AGENT_SYSTEM_PROMPT = """You are a Research Agent specializing in web search
and information gathering. You have access to web search tools to find accurate,
up-to-date information.

Rules:
1. Always cite your sources with URLs.
2. Distinguish between facts and opinions.
3. Cross-reference multiple sources when possible.
4. Summarize findings clearly and concisely.
5. If you cannot find reliable information, say so explicitly.
"""

CODING_AGENT_SYSTEM_PROMPT = """You are a Coding Agent specializing in code generation,
debugging, and software engineering tasks. You can write, execute, and test code
in a sandboxed environment.

Rules:
1. Write clean, well-documented, production-quality code.
2. Always include error handling and edge cases.
3. Test your code in the sandbox before returning results.
4. Follow the language's idiomatic conventions and best practices.
5. If code execution fails, analyze the error and fix it.
"""

ANALYSIS_AGENT_SYSTEM_PROMPT = """You are an Analysis Agent specializing in data analysis,
database queries, and API integrations. You can query databases, call APIs,
and perform statistical analysis.

Rules:
1. Always use parameterized queries to prevent SQL injection.
2. Validate and sanitize all input data before processing.
3. Provide clear interpretations of analytical results.
4. Include relevant statistics and confidence levels.
5. Visualize data when it aids understanding.
"""

# ==========================================================
# 9. ERROR MESSAGES — Standardized error responses
# ==========================================================

ERROR_MESSAGES: dict[str, str] = {
    "auth_missing": "Authentication required. Provide a valid API key in the X-API-Key header.",
    "auth_invalid": "Invalid API key. Please check your credentials.",
    "rate_limited": "Rate limit exceeded. Please wait {retry_after} seconds before retrying.",
    "task_not_found": "Task with ID '{task_id}' not found.",
    "agent_timeout": "Agent '{agent_type}' timed out after {timeout}s on subtask '{subtask_id}'.",
    "orchestrator_timeout": "Task '{task_id}' exceeded the maximum processing time of {timeout}s.",
    "llm_error": "LLM provider '{provider}' returned an error: {error}",
    "mcp_connection_failed": "Failed to connect to MCP server '{server_name}': {error}",
    "mcp_tool_not_found": "MCP tool '{tool_name}' not found on server '{server_name}'.",
    "validation_error": "Request validation failed: {details}",
    "internal_error": "An internal error occurred. Request ID: {request_id}",
}
