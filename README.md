# DevAgent — Multi-Agent Orchestration System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-green.svg)](https://docs.pydantic.dev/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/ORM-SQLAlchemy%202.0%20Async-red.svg)](https://docs.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**DevAgent** is an enterprise-grade autonomous multi-agent orchestration platform designed to decompose, schedule, execute, cross-validate, and synthesize complex technical workflows using specialized AI agents ([Research](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L35), [Coding](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L36), and [Analysis](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L37)). The platform natively integrates with the **Model Context Protocol (MCP)**, supports multi-provider LLM failover, maintains short-term conversational context via Redis, and guarantees persistent, audit-compliant state management with async PostgreSQL.

---

## Table of Contents

- [1. System Overview & Architecture](#1-system-overview--architecture)
  - [Core Orchestration Paradigm](#core-orchestration-paradigm)
  - [Specialized Agent Roles](#specialized-agent-roles)
  - [The DAG Pipeline Lifecycle](#the-dag-pipeline-lifecycle)
  - [High-Level Architecture Diagram](#high-level-architecture-diagram)
- [2. Phase 1 Retrospective: Infrastructure & Environment Foundation](#2-phase-1-retrospective-infrastructure--environment-foundation)
  - [Build System & Dependency Boundary (`pyproject.toml`)](#build-system--dependency-boundary-pyprojecttoml)
  - [Environment Hardening & Secret Isolation (`.env.example`)](#environment-hardening--secret-isolation-envexample)
  - [Operational Tooling & Workflow Automation (`Makefile`)](#operational-tooling--workflow-automation-makefile)
  - [Configuration Domain & Immutable System Constants (`src/config/`)](#configuration-domain--immutable-system-constants-srcconfig)
- [3. Phase 2 Deep-Dive: Data Contracts, State Machines & Persistence Engine](#3-phase-2-deep-dive-data-contracts-state-machines--persistence-engine)
  - [Data Contract Architecture (`src/models/schemas.py`)](#data-contract-architecture-srcmodelsschemaspy)
  - [LangGraph State Engine & Reducer Semantics (`src/models/state.py`)](#langgraph-state-engine--reducer-semantics-srcmodelsstatepy)
  - [Relational Persistence Layer (`src/models/database.py`)](#relational-persistence-layer-srcmodelsdatabasepy)
  - [Async Database Connection Pool & Session Lifecycle (`src/db/session.py`)](#async-database-connection-pool--session-lifecycle-srcdbsessionpy)
  - [High-Performance Caching & Shared Agent Memory (`src/db/redis_client.py`)](#high-performance-caching--shared-agent-memory-srcdbredis_clientpy)
  - [Unified Package Facades (`src/models/__init__.py` & `src/db/__init__.py`)](#unified-package-facades-srcmodels__init__py--srcdb__init__py)
  - [Production Safeguards & Architectural Invariants](#production-safeguards--architectural-invariants)
- [4. Phase 3 Deep-Dive: Core Orchestration Engine & Agent Framework](#4-phase-3-deep-dive-core-orchestration-engine--agent-framework)
  - [Multi-Provider LLM Abstraction & Automatic Failover (`src/llm/`)](#multi-provider-llm-abstraction--automatic-failover-srcllm)
  - [Async Token & Cost Accounting Engine (`src/llm/callbacks.py`)](#async-token--cost-accounting-engine-srcllmcallbackspy)
  - [Tool Abstraction Layer & LangChain Adapter (`src/tools/`)](#tool-abstraction-layer--langchain-adapter-srctools)
  - [Base Agent ReAct Subgraph & Execution Loop (`src/agents/base.py`)](#base-agent-react-subgraph--execution-loop-srcagentsbasepy)
  - [Specialized Agent Registry & Factory (`src/agents/registry.py`)](#specialized-agent-registry--factory-srcagentsregistrypy)
  - [Topological Task Decomposition & DAG Validation (`src/orchestrator/planner.py`)](#topological-task-decomposition--dag-validation-srcorchestratorplannerpy)
  - [Dependency-Aware Concurrent Dispatcher (`src/orchestrator/dispatcher.py`)](#dependency-aware-concurrent-dispatcher-srcorchestratordispatcherpy)
  - [Top-Level Orchestration Pipeline & Graph Engine (`src/orchestrator/engine.py`)](#top-level-orchestration-pipeline--graph-engine-srcorchestratorenginepy)
  - [Phase 3 Production Safeguards & Resilience Matrix](#phase-3-production-safeguards--resilience-matrix)
- [5. Interactive Execution Trace & Metric Lifecycle](#5-interactive-execution-trace--metric-lifecycle)
  - [End-to-End Execution Walkthrough: "Research & Benchmark Vector Stores"](#end-to-end-execution-walkthrough-research--benchmark-vector-stores)
  - [Step-by-Step State Mutation Trace](#step-by-step-state-mutation-trace)
  - [Token, Latency, and Financial Cost Lifecycle](#token-latency-and-financial-cost-lifecycle)
- [6. Repository Structure](#6-repository-structure)
- [7. Getting Started](#7-getting-started)

---

## 1. System Overview & Architecture

### Core Orchestration Paradigm

In enterprise environments, monolithic LLM prompts fail on multifaceted engineering tasks due to context dilution, hallucination compounding, and inability to safely invoke heterogeneous tools. **DevAgent** resolves this through **Directed Acyclic Graph (DAG) Multi-Agent Orchestration**:

1. **Decoupled Planning vs. Execution:** An [Orchestrator](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L246) decomposes unbounded user objectives into discrete, bounded [SubTasks](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L238) with explicit dependency graphs.
2. **Agent Specialization:** Subtasks are routed exclusively to specialized agents equipped with role-constrained system prompts, dedicated tool registries, and isolated execution scopes.
3. **Isolated Agent Execution Loops:** Each agent operates within a bounded ReAct cycle (Reason + Act), updating its private execution state without polluting the global task state.
4. **Deterministic Synthesis & Consensus:** Execution outputs pass through strict validation gates before being synthesized into a coherent final response with multi-agent source attribution and confidence scoring.

### Specialized Agent Roles

DevAgent provisions three specialized agent personas, governed by [AgentType](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L24):

| Agent Type | System Prompt & Core Competency | Tooling Matrix | Output Signature |
|:---|:---|:---|:---|
| **[RESEARCH](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L35)** | Web exploration, technical documentation ingestion, literature search, and source-attributed fact gathering. | Tavily Search, SerpAPI, Web Scraper, Document Parser | Markdown briefing, cited source URLs, factual extracts. |
| **[CODING](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L36)** | Polyglot code generation, architectural design, debugging, unit test creation, and sandboxed execution. | Docker Sandbox Code Executor, GitHub API, AST Analyzer, File Manager | Production-ready code modules, test suites, execution logs. |
| **[ANALYSIS](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L37)** | Quantitative benchmarking, database querying, statistical modeling, latency/cost profiling, and data visualization. | Async Database Engine, REST API Client, Statistical Profiler, Chart Visualizer | Tabular benchmarks, JSON payloads, metric tradeoff charts. |

### The DAG Pipeline Lifecycle

The task execution pipeline operates as a deterministic finite-state machine with five canonical lifecycle stages:

```
[ User Request ] ───▶ Planning ───▶ Dispatching ───▶ Parallel Execution ───▶ Validation ───▶ Synthesis ───▶ [ TaskResponse ]
                         │                                 │                    │
                         ▼                                 ▼                    ▼
                   [Plan Rejected]                   [Retry Loop]        [Consensus Fail]
```

1. **Planning (`PLANNING`):** The orchestrator evaluates the [TaskCreate](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L86) request. It runs topological decomposition to generate an ordered list of [SubTaskCreate](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L238) instances, establishing execution orders and prerequisite dependency arrays (`dependencies: list[str]`).
2. **Dispatching (`DISPATCHING`):** The orchestrator checks the DAG for unscheduled subtasks whose prerequisite dependencies have transitioned to `COMPLETED`. Ready subtasks are dispatched to the execution queue up to the concurrency ceiling (`AGENT_MAX_CONCURRENCY=5`).
3. **Execution (`EXECUTING`):** Specialized agents pick up their assigned [SubTaskState](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L168) and instantiate a localized [AgentState](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L94). Agents execute localized ReAct cycles, interacting with internal tools or external MCP servers while appending messages and tool call records to their append-only state reducers.
4. **Validation (`VALIDATING`):** Subtask outputs are intercepted by validator nodes. The system verifies output schema compliance, checks confidence metrics against minimum thresholds, inspects tool exit codes, and cross-references source URLs. Failed subtasks are routed to the retry pipeline (`RETRYING`) up to `AGENT_MAX_RETRIES=3`.
5. **Synthesis (`SYNTHESIZING`):** Once all subtasks achieve terminal success, the orchestrator aggregates outputs, computes weighted confidence scores across all agents, reconciles token usage, and produces the unified [TaskResult](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L479) before transitioning to `COMPLETED`.

### High-Level Architecture Diagram

```mermaid
flowchart TB
    subgraph ClientLayer [Client & Ingestion Layer]
        User([Client / API Consumer])
        FastAPI[FastAPI REST & WebSocket Gateway]
        RateLimiter[Sliding-Window Rate Limiter]
    end

    subgraph ConfigLayer [Configuration & Constants]
        Settings[src.config.Settings<br/>Pydantic BaseSettings]
        Constants[src.config.Constants<br/>Enums, Prompts, Pricing]
    end

    subgraph OrchestrationLayer [LangGraph Orchestration Engine]
        OrchState[(OrchestratorState)]
        PlannerNode[Planner Node]
        DispatchNode[Dispatcher Node]
        MonitorNode[DAG Dependency Monitor]
        ValidatorNode[Validation Gate]
        SynthNode[Synthesizer Node]
    end

    subgraph AgentLayer [Specialized Agent Subgraphs]
        ResearchAgent[Research Agent<br/>ReAct Loop]
        CodingAgent[Coding Agent<br/>Sandbox Runner]
        AnalysisAgent[Analysis Agent<br/>Query & Benchmark]
    end

    subgraph ToolingAndMCP [Tool Registry & MCP Integration]
        InternalTools[Internal Tools<br/>Search, Code Exec, SQL]
        MCPClient[MCP Client Hub<br/>STDIO / SSE / Streamable HTTP]
        MCPServers[External MCP Servers<br/>Chrome DevTools, GitHub, MongoDB]
    end

    subgraph PersistenceLayer [State & Persistence Infrastructure]
        RedisPool[(Redis 7.0+ Pool<br/>Shared Context, Sessions, Locks)]
        Postgres[(PostgreSQL 16+ Pool<br/>Tasks, Subtasks, Logs, Metrics)]
    end

    User -->|POST /api/v1/tasks| FastAPI
    FastAPI --> RateLimiter
    RateLimiter -->|Validated TaskCreate| PlannerNode
    Settings -.-> OrchestrationLayer
    Constants -.-> OrchestrationLayer

    PlannerNode --> OrchState
    OrchState --> DispatchNode
    DispatchNode --> MonitorNode

    MonitorNode -->|SubTask 1: Research| ResearchAgent
    MonitorNode -->|SubTask 2: Coding| CodingAgent
    MonitorNode -->|SubTask 3: Analysis| AnalysisAgent

    ResearchAgent <--> RedisPool
    CodingAgent <--> RedisPool
    AnalysisAgent <--> RedisPool

    ResearchAgent --> ToolingAndMCP
    CodingAgent --> ToolingAndMCP
    AnalysisAgent --> ToolingAndMCP
    ToolingAndMCP --> MCPClient
    MCPClient --> MCPServers

    ResearchAgent -->|SubTaskResult| ValidatorNode
    CodingAgent -->|SubTaskResult| ValidatorNode
    AnalysisAgent -->|SubTaskResult| ValidatorNode

    ValidatorNode --> SynthNode
    SynthNode -->|TaskResult| Postgres
    SynthNode -->|TaskResponse| FastAPI
    FastAPI -->|JSON Response / Stream| User
```

---

## 2. Phase 1 Retrospective: Infrastructure & Config

Phase 1 established the deterministic foundation of DevAgent. In distributed multi-agent systems, runtime failures frequently originate from unvalidated environment configurations, unpinned dependencies, missing driver stubs, or unmanaged secrets. Phase 1 eliminated these failure classes before introducing orchestration code.

### Build System & Dependency Boundary (`pyproject.toml`)

* **File Location:** [`pyproject.toml`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/pyproject.toml)
* **Architecture Role:** Declarative single source of truth for package metadata, external dependencies, optional feature sets, and code quality toolchains conforming to PEP 517/518 and PEP 621.
* **Component Breakdown:**
  * **Core Dependencies (`dependencies`):**
    * *Agent & Orchestration:* `langchain>=0.3.0`, `langgraph>=0.2.0`, `langchain-core>=0.3.0`.
    * *LLM Provider SDKs:* `langchain-google-genai>=2.0.0` (primary default), `langchain-openai>=0.2.0`, `langchain-anthropic>=0.2.0`.
    * *Data Validation & Settings:* `pydantic>=2.5.0`, `pydantic-settings>=2.1.0`.
    * *Web & Gateway:* `fastapi>=0.115.0`, `uvicorn[standard]>=0.30.0`, `websockets>=13.0`, `python-jose>=3.3.0`.
    * *Storage & Persistence Drivers:* `sqlalchemy[asyncio]>=2.0.0`, `asyncpg>=0.29.0`, `alembic>=1.13.0`, `redis[hiredis]>=5.0.0` (with native C parser for high-throughput serialization).
    * *Vector Search & Embeddings:* `pinecone-client>=3.0.0`, `langchain-huggingface>=0.1.0`.
    * *Model Context Protocol:* `mcp>=1.0.0`.
    * *Observability & Resiliency:* `structlog>=24.1.0`, `tenacity>=9.0.0`, `tiktoken>=0.7.0`, OpenTelemetry suite, `prometheus-client>=0.21.0`.
  * **Optional Feature Groups (`[project.optional-dependencies]`):**
    * `dev`: Ruff, Mypy, pre-commit, IPython, Rich.
    * `test`: Pytest, `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `fakeredis`, `respx`, `factory-boy`.
    * `docs`: MkDocs Material suite.
  * **CLI Entrypoints (`[project.scripts]`):**
    * `devagent = "src.api.main:run"`
    * `devagent-mcp = "src.mcp.server:run"`
  * **Linter & Static Type Analysis Configurations:**
    * *Ruff (`[tool.ruff]`):* Enforces 13 linter rule categories including pycodestyle (`E`, `W`), Pyflakes (`F`), isort (`I`), pep8-naming (`N`), pyupgrade (`UP`), bugbear (`B`), simplify (`SIM`), type-checking (`TCH`), async rules (`ASYNC`), bandit security (`S`), and print statement bans (`T20`).
    * *Mypy (`[tool.mypy]`):* Configured in strict mode (`strict = true`, `disallow_untyped_defs = true`, `warn_return_any = true`).
    * *Pytest & Coverage:* Configured for automated async event loop discovery, test markers (`unit`, `integration`, `slow`), and an enforced 80% minimum coverage threshold (`fail_under = 80`).

### Environment Hardening & Secret Isolation (`.env.example`)

* **File Location:** [`.env.example`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/.env.example)
* **Architecture Role:** Exhaustive, production-ready environment variable blueprint. Documents all configurable operational flags across 11 discrete subsystem domains.
* **Subsystem Coverage:**
  1. *Application Governance:* Environment tag (`APP_ENV`), debug toggles, network host/port bindings, JWT secret keys, and client API keys.
  2. *LLM Provider Hub:* Model selectors, temperature ceilings (0.1 for deterministic routing), token ceilings (4096), timeout thresholds, and provider-specific credentials (OpenAI, Azure OpenAI, Anthropic, Google Gemini).
  3. *PostgreSQL Pool:* Connection URIs, credentials, and connection pool sizing (`POSTGRES_POOL_SIZE=10`, `POSTGRES_MAX_OVERFLOW=20`, `POSTGRES_POOL_TIMEOUT=30`).
  4. *Redis Cache & Memory:* Host, port, DB indexing, TLS flags (`REDIS_SSL`), and default/session TTL policies (3600s / 86400s).
  5. *Vector Database:* Pinecone API keys, environment regions, index names, vector dimension specifications (1536), and similarity metrics (`cosine`).
  6. *Agent Tooling Keys:* Tavily search credentials, GitHub access tokens, and code execution container boundaries (memory ceilings and timeouts).
  7. *Model Context Protocol (MCP):* Discovery switches, client timeouts, retry limits, server-specific auth tokens, and DevAgent's hosted MCP server configuration.
  8. *Observability & Telemetry:* OpenTelemetry OTLP gRPC collector endpoints, sampling ratios, Prometheus scraping port (9090), and cumulative financial alert ceilings (`COST_ALERT_THRESHOLD_USD=50.00`).
  9. *External Webhooks:* Slack alerting URLs, Notion database UUIDs, and GitHub webhook HMAC secrets.
  10. *Security & Rate Limiting:* API request quotas (100 req/min), LLM rate throttling (60 RPM / 100k TPM), CORS origins, and payload size bounds.
  11. *Orchestration Thresholds:* Max subtasks per query (10), retry caps (3), and global task timeout (300s).

### Operational Tooling & Workflow Automation (`Makefile`)

* **File Location:** [`Makefile`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/Makefile)
* **Architecture Role:** Cross-platform operational automation abstraction layer, standardizing developer workflows and CI/CD pipelines into uniform targets.
* **Target Categories:**
  * *Setup & Lifecycle:* `make install`, `make install-dev`, `make install-all`, `make clean`.
  * *Application Execution:* `make run` (Uvicorn reload development mode), `make run-prod` (multi-worker production mode), `make mcp-server` (DevAgent MCP daemon).
  * *Quality Assurance:* `make lint` (Ruff verification), `make format` (Ruff auto-formatting + import sorting), `make type-check` (Mypy verification), `make check` (unified linter + type-checker).
  * *Testing:* `make test`, `make test-unit`, `make test-integration`, `make test-cov` (HTML + terminal coverage reporting).
  * *Database Migrations:* `make db-migrate msg="..."`, `make db-upgrade`, `make db-downgrade`, `make db-seed`.
  * *Docker Operations:* `make docker-up`, `make docker-down`, `make docker-build`, `make docker-fresh` (volume wipe and cold rebuild).
  * *MCP Tool Operations:* `make mcp-discover`, `make mcp-list`.
  * *Sanity Checks:* `make env-check`, `make tree`.

### Configuration Domain & Immutable System Constants (`src/config/`)

#### [`src/config/settings.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/settings.py) — Validated Configuration Engine
* **Architectural Purpose:** Reads environment variables and local `.env` files, validates data types, enforces ranges, masks secrets, and provides computed properties. Modules access configuration exclusively through the cached singleton function [get_settings()](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/settings.py#L350) (`@lru_cache(maxsize=1)`), completely eliminating uncontrolled `os.environ` lookups.
* **Core Classes & Methods:**
  * [Settings](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/settings.py#L35): Subclasses `BaseSettings` with `SettingsConfigDict(case_sensitive=True, extra="ignore")`.
  * [SecretStr](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/settings.py#L24) Protection: API keys (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `POSTGRES_PASSWORD`, `APP_SECRET_KEY`) wrap values in Pydantic's `SecretStr` to prevent token leakage in debug logs, stack traces, and JSON outputs.
  * Computed Connection Properties:
    * [database_url_computed](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/settings.py#L247): Dynamically synthesizes `postgresql+asyncpg://user:pass@host:port/db` if `DATABASE_URL` is not explicitly declared.
    * [redis_url_computed](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/settings.py#L261): Dynamically builds `redis://` or `rediss://` (for TLS) connection strings with URL-encoded passwords.
  * Model Validators:
    * [validate_llm_provider_keys](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/settings.py#L284): Validates that the chosen `LLM_PROVIDER` has a non-empty API key configured before the application boots, preventing runtime orchestration failure.
    * [validate_production_settings](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/settings.py#L318): Prevents application boot in production if `APP_SECRET_KEY` retains default placeholder text (`CHANGE_ME`), and issues loud warnings if `APP_DEBUG=true`.

#### [`src/config/constants.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py) — Immutable System Primitives
* **Architectural Purpose:** Defines deterministic, compile-time constants, enums, pricing matrices, system prompts, and standard error messages that never vary across environments.
* **Core Primitives & Structures:**
  * [AgentType(str, Enum)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L24): Defines `RESEARCH`, `CODING`, and `ANALYSIS` with self-describing metadata properties (`description`, `default_tools`).
  * [TaskStatus(str, Enum)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L64): Finite lifecycle states (`PENDING`, `PLANNING`, `EXECUTING`, `VALIDATING`, `SYNTHESIZING`, `COMPLETED`, `FAILED`, `RETRYING`, `CANCELLED`, `TIMED_OUT`) with convenience properties `is_terminal` and `is_active`.
  * [SubTaskStatus(str, Enum)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L114): Granular subtask states (`PENDING`, `ASSIGNED`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `SKIPPED`).
  * [Priority(IntEnum)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L129): Urgency ranking from `CRITICAL = 1` to `LOW = 4` allowing natural comparison operations (`Priority.CRITICAL < Priority.LOW`).
  * [LLMProvider(str, Enum)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L156): Provider mappings paired with LangChain dynamic class string resolutions.
  * System Pricing Table [LLM_COST_PER_MILLION_TOKENS](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L230): Input and output token pricing per million tokens across 8 major models (GPT-4o, GPT-4o-mini, Gemini-1.5-Flash, Gemini-1.5-Pro, Claude-3.5-Sonnet, etc.).
  * Role-Specific System Prompts: Base system instructions for [Orchestrator](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L246), [Research Agent](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L263), [Coding Agent](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L275), and [Analysis Agent](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L287).
  * Standardized System Errors ([ERROR_MESSAGES](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L303)): Canonical error response templates for auth, timeouts, rate limits, and MCP failures.

---

## 3. Phase 2 Deep-Dive: Data Contracts, State Machines & Persistence Engine

Phase 2 constructed the core operational data infrastructure of DevAgent. It establishes how data enters via the API, mutates through cyclical LangGraph execution graphs, caches in Redis, and persists to PostgreSQL.

```
       ┌────────────────────────────────────────────────────────┐
       │             API Boundary: Pydantic v2                  │
       │  (TaskCreate, TaskResponse, SubTaskResponse, etc.)      │
       └──────────────────────────┬─────────────────────────────┘
                                  │ Transforms / Ingests
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │         LangGraph Runtime: TypedDict + Reducers        │
       │    (OrchestratorState, AgentState, SubTaskState)       │
       └──────────────────────────┬─────────────────────────────┘
                                  │ Serializes / Syncs
                                  ▼
       ┌──────────────────────────┴─────────────────────────────┐
       │                                                        │
       ▼                                                        ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│  Redis Caching & Shared Mem  │        │   PostgreSQL 16+ Async ORM   │
│ (devagent:memory:, sessions) │        │ (TaskRecord, SubTaskRecord)  │
└──────────────────────────────┘        └──────────────────────────────┘
```

---

### Data Contract Architecture (`src/models/schemas.py`)

* **File Location:** [`src/models/schemas.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py)
* **Architecture Role:** Defines the public data contracts for DevAgent. Governs API request validation, response serialization, agent communication payloads, tool invocation structures, and pagination metadata.
* **Component Walkthrough:**

| Schema Class | Base Inheritance | Key Fields & Types | Architectural Role & Safeguards |
|:---|:---|:---|:---|
| [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51) | `BaseModel` | `ConfigDict` | Root configuration: sets `from_attributes=True` for seamless SQLAlchemy model conversion, `populate_by_name=True`, `use_enum_values=True`, and `str_strip_whitespace=True`. |
| [TimestampMixin](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L69) | `BaseModel` | `created_at`, `updated_at: datetime` | Enforces timezone-aware UTC timestamps (`default_factory=lambda: datetime.now(timezone.utc)`). |
| [TaskCreate](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L86) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51) | `description: str`, `priority: Priority`, `metadata: dict`, `callback_url: str \| None` | User task submission contract. Includes [clean_description](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L124) validator to strip extra whitespace, collapse newlines, and enforce a length range between 10 and 10,000 characters. |
| [TaskUpdate](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L132) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51) | `status: TaskStatus \| None`, `result: TaskResult \| None`, `metadata: dict \| None` | Partial update schema for updating execution status and results. |
| [TaskResponse](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L152) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51), [TimestampMixin](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L69) | `id: str`, `status: TaskStatus`, `subtasks: list[SubTaskResponse]`, `result: TaskResult \| None`, `total_tokens: int`, `total_cost_usd: float`, `duration_seconds: float \| None` | Comprehensive API response schema representing complete task state, child subtask progress, execution metrics, and final synthesized results. |
| [TaskSummary](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L219) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51), [TimestampMixin](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L69) | `id: str`, `description: str`, `status: TaskStatus`, `subtask_count: int`, `total_cost_usd: float` | High-performance lightweight projection for paginated list endpoints, truncating descriptions to 200 characters and omitting verbose subtask lists. |
| [SubTaskCreate](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L238) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51) | `description: str`, `agent_type: AgentType`, `dependencies: list[str]`, `tools_required: list[str]`, `order: int` | Internal contract produced by the Orchestrator Planner. Encapsulates topological dependency IDs and tool access rules. |
| [SubTaskResponse](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L275) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51), [TimestampMixin](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L69) | `id: str`, `task_id: str`, `agent_type: AgentType`, `status: SubTaskStatus`, `result: SubTaskResult \| None`, `token_usage: TokenUsage \| None` | Full representation of an individual subtask execution, including assigned agent, retry counts, token usage, and execution duration. |
| [ToolCallRequest](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L334) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51) | `id: str`, `tool_name: str`, `arguments: dict[str, Any]`, `source: str` | Structured representation of an agent's intent to invoke an internal tool or an external MCP server capability. |
| [ToolCallResponse](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L360) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51) | `tool_call_id: str`, `tool_name: str`, `result: Any`, `error: str \| None`, `is_error: bool`, `duration_seconds: float` | Encapsulates tool output or error state, capturing timing metrics for latency profiling. |
| [AgentMessage](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L399) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51) | `role: str`, `content: str`, `agent_type: AgentType \| None`, `tool_calls: list`, `tool_responses: list` | Serializable representation of conversation history supporting system, human, AI, and tool roles. |
| [SubTaskResult](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L442) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51) | `output: str`, `confidence: float`, `sources: list[str]`, `raw_data: dict`, `tool_calls_made: int` | Output artifact produced by a specialized agent upon completing a subtask, featuring self-assessed confidence (0.0 to 1.0) and source citations. |
| [TaskResult](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L479) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51) | `summary: str`, `detailed_output: str`, `subtask_results: list[SubTaskResult]`, `overall_confidence: float`, `sources: list[str]` | Unified final synthesis aggregating all completed subtasks into a consolidated response with weighted confidence scoring. |
| [TokenUsage](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L519) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51) | `prompt_tokens: int`, `completion_tokens: int`, `total_tokens: int`, `model: str`, `estimated_cost_usd: float` | Metric contract tracking token consumption. Features an auto-computing validator [compute_total](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L539) to dynamically calculate `total_tokens = prompt + completion`. |
| [CostRecord](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L549) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51), [TimestampMixin](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L69) | `task_id: str`, `subtask_id: str \| None`, `provider: str`, `model: str`, `cost_usd: float` | Granular financial record persisted for billing auditing and cost alert thresholds. |
| [PaginationParams](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L569) / [PaginatedResponse](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L591) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51) | `page: int`, `page_size: int`, `offset: int`, `total: int`, `items: list[Any]` | Generic pagination wrapper calculating SQL offset (`(page - 1) * page_size`) with page size ceilings (`le=100`). |
| [TaskFilter](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L606) | [BaseSchema](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L51) | `status`, `priority`, `agent_type`, `created_after`, `created_before`, `search` | Multi-criteria query filter supporting status filtering, priority checks, and full-text search parameters. |

* **Forward Reference Resolution:** The file concludes by executing explicit model rebuilds (`TaskUpdate.model_rebuild()`, `TaskResponse.model_rebuild()`, `SubTaskResponse.model_rebuild()`) to resolve circular self-referencing type definitions between task responses, subtask responses, and task results.

---

### LangGraph State Engine & Reducer Semantics (`src/models/state.py`)

* **File Location:** [`src/models/state.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py)
* **Architecture Role:** Defines the execution state flowing through LangGraph nodes. LangGraph requires states to be structured as `TypedDict` objects. This module configures state reducers to manage state merging across parallel node executions and cyclical transitions.
* **Component Walkthrough:**

#### 1. [AgentState](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L94) (`TypedDict, total=False`)
Manages execution state for an individual specialized agent working on a single assigned subtask:
* **Identity Scope:** `agent_type: str`, `subtask_id: str`, `task_id: str`, `subtask_description: str`.
* **Append-Only Reducers (`Annotated[list, operator.add]`):**
  * `messages`: The agent's conversation history. By defining `Annotated[list[MessageRecord], operator.add]`, LangGraph appends newly returned messages to the existing list rather than overwriting previous context.
  * `tool_calls`: Audit log of every [ToolCallRecord](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L41) executed during the ReAct loop.
  * `token_usage`: List of [TokenUsageRecord](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L83) snapshots capturing per-turn token usage.
* **Execution Control & Loop Guard:**
  * `iteration_count: int`: Current iteration in the agent's ReAct cycle.
  * `max_iterations: int`: Guard ceiling (default: 10) to prevent infinite LLM execution loops.
  * `should_continue: bool`: Boolean flag evaluated by conditional edges (`tools_condition`) to route to tool execution or finalize output.
* **Outputs & Metrics:** `result: dict | None`, `error: str | None`, `total_tokens: int`, `total_cost_usd: float`, `duration_seconds: float`.

#### 2. [SubTaskState](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L168) (`TypedDict, total=False`)
Tracks the real-time lifecycle of an individual subtask within the orchestrator's global dependency graph:
* Tracks `subtask_id`, `description`, `agent_type`, `status`, `order`, `dependencies: list[str]`, `tools_required: list[str]`, `result`, `error`, `retry_count`, and ISO 8601 timestamps.

#### 3. [OrchestratorState](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L197) (`TypedDict, total=False`)
Governs the top-level LangGraph orchestration graph for a user request:
* **Task Context:** `task_id`, `task_description`, `priority`, `metadata`, `callback_url`.
* **Decomposition Plan:** `plan: list[dict]`, `planning_reasoning: str`.
* **Subtask Registry & Queues:**
  * `subtask_states: dict[str, SubTaskState]`: Complete dictionary of all subtasks keyed by UUID.
  * `pending_subtasks: list[str]`: Unscheduled subtasks waiting for dependencies.
  * `active_subtasks: list[str]`: Subtasks currently executing across parallel agents.
  * `completed_subtasks: Annotated[list[str], operator.add]`: Append-only list of finished subtask IDs.
  * `failed_subtasks: Annotated[list[str], operator.add]`: Append-only list of failed subtask IDs.
* **Cross-Agent Shared Memory:**
  * `shared_context: dict[str, Any]`: Context hub where intermediate agent results (e.g., Research API docs) are staged for consumption by downstream agents (e.g., Coding agent).
* **Consensus & Synthesis:**
  * `subtask_results: Annotated[list[dict], operator.add]`: Append-only aggregation of validated agent outputs.
  * `final_result: dict | None`: Synthesized [TaskResult](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L479) dictionary.
* **Orchestrator Audit:** `messages: Annotated[list[MessageRecord], operator.add]`, `total_tokens: int`, `total_cost_usd: float`, `duration_seconds: float`.

#### 4. State Factory Functions
* [create_agent_state(...)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L301): Returns an initialized [AgentState](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L94) with zero-value counters, empty append-only lists, and loop guards (`max_iterations=10`).
* [create_orchestrator_state(...)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L344): Returns an initialized [OrchestratorState](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L197) with UTC ISO timestamps, empty dependency queues, and default status `pending`.
* *Design Rationale:* Prevents runtime `KeyError` exceptions when LangGraph nodes read optional fields before they have been populated.

---

### Relational Persistence Layer (`src/models/database.py`)

* **File Location:** [`src/models/database.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/database.py)
* **Architecture Role:** Persistent relational storage using SQLAlchemy 2.0 async declarative mapping (`Mapped[T]` and `mapped_column`). Stores historical tasks, subtasks, audit logs, and token/cost metrics in PostgreSQL.
* **Component Walkthrough:**

```mermaid
erDiagram
    TASKS ||--o{ SUBTASKS : "decomposes into (1:N)"
    TASKS ||--o{ EXECUTION_LOGS : "generates audit (1:N)"
    TASKS ||--o{ AGENT_METRICS : "tracks usage (1:N)"
    SUBTASKS ||--o{ EXECUTION_LOGS : "logs actions (1:N)"
    SUBTASKS ||--o{ AGENT_METRICS : "records costs (1:N)"

    TASKS {
        uuid id PK
        text description
        string status
        integer priority
        json result
        json metadata
        integer total_tokens
        float total_cost_usd
        timestamp created_at
        timestamp completed_at
    }

    SUBTASKS {
        uuid id PK
        uuid task_id FK
        text description
        string agent_type
        string status
        integer order
        json dependencies
        json tools_required
        json result
        json token_usage
    }

    EXECUTION_LOGS {
        uuid id PK
        uuid task_id FK
        uuid subtask_id FK
        string agent_type
        string action
        json details
        string level
        timestamp created_at
    }

    AGENT_METRICS {
        uuid id PK
        uuid task_id FK
        uuid subtask_id FK
        string provider
        string model
        integer prompt_tokens
        integer completion_tokens
        integer total_tokens
        float cost_usd
        float duration_seconds
        timestamp created_at
    }
```

* **Model Inventory:**
  1. [Base(DeclarativeBase)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/database.py#L56): Common declarative base for Alembic migrations and table creation.
  2. [TimestampMixin](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/database.py#L73): Mixin providing timezone-aware `created_at` and `updated_at` columns using `DateTime(timezone=True)`.
  3. [TaskRecord](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/database.py#L100) (`tasks` table):
     * *Primary Key:* `id: UUID` (v4).
     * *Columns:* `description (Text)`, `status (String(20))`, `priority (Integer)`, `result (JSON)`, `error_message (Text)`, `retry_count (Integer)`, `metadata_ (JSON)`, `callback_url (String(2048))`, `total_tokens (Integer)`, `total_cost_usd (Float)`, `duration_seconds (Float)`, `completed_at (DateTime)`.
     * *Relationships:* `subtasks` (with `cascade="all, delete-orphan"`, `lazy="selectin"` for eager loading), `execution_logs`, and `metrics`.
     * *Indexes:* Composite index `ix_tasks_status_priority` on `(status, priority)` for queue querying, and `ix_tasks_created_at` for temporal ordering.
  4. [SubTaskRecord](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/database.py#L248) (`subtasks` table):
     * *Primary Key:* `id: UUID`.
     * *Foreign Key:* `task_id -> tasks.id` with `ondelete="CASCADE"`.
     * *Columns:* `description`, `agent_type`, `status`, `order (Integer)`, `dependencies (JSON)`, `tools_required (JSON)`, `result (JSON)`, `error_message`, `retry_count`, `token_usage (JSON)`, `duration_seconds`.
     * *Indexes:* `ix_subtasks_task_status` on `(task_id, status)` and `ix_subtasks_task_order` on `(task_id, order)`.
  5. [ExecutionLog](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/database.py#L401) (`execution_logs` table):
     * Immutable audit trail recording events (`llm_call`, `tool_call`, `tool_result`, `status_change`, `error`, `retry`, `planning`, `synthesis`).
     * Features foreign keys to both `task_id` and optional `subtask_id`, log `level` (`info`, `warning`, `error`), and JSON `details`.
  6. [AgentMetric](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/database.py#L504) (`agent_metrics` table):
     * Stores granular metrics for each individual LLM interaction: `provider`, `model`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `cost_usd`, and `duration_seconds`.

---

### Async Database Connection Pool & Session Lifecycle (`src/db/session.py`)

* **File Location:** [`src/db/session.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/session.py)
* **Architecture Role:** Manages the lifecycle of async PostgreSQL connections using SQLAlchemy's `create_async_engine` and `async_sessionmaker`.
* **Component Walkthrough:**
  * [_create_engine()](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/session.py#L61): Instantiates the `AsyncEngine` with connection pooling:
    * `pool_size=POSTGRES_POOL_SIZE` (default: 10 persistent connections).
    * `max_overflow=POSTGRES_MAX_OVERFLOW` (default: 20 burst connections).
    * `pool_timeout=POSTGRES_POOL_TIMEOUT` (30-second checkout ceiling).
    * `pool_pre_ping=True`: Verifies connection liveness before checking out from the pool to recover from closed database sockets.
    * `pool_recycle=3600`: Recycles idle connections after 1 hour to prevent stale connections.
    * `connect_args={"server_settings": {"jit": "off"}}`: Disables PostgreSQL JIT compiler to reduce query latency on short transaction queries.
  * [_create_session_factory(engine)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/session.py#L108): Configures `async_sessionmaker[AsyncSession]` with `expire_on_commit=True`, `autocommit=False`, and `autoflush=False`.
  * [init_db()](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/session.py#L136) & [close_db()](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/session.py#L161): Application lifecycle hooks invoked during FastAPI startup and shutdown. Automatically creates missing schema tables during development (`conn.run_sync(Base.metadata.create_all)`).
  * [get_async_session()](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/session.py#L211): FastAPI dependency generator yielding request-scoped async sessions. Automatically commits on successful completion, rolls back on exceptions, and closes the session on exit:
    ```python
    @app.post("/tasks")
    async def create_task(
        task: TaskCreate,
        session: AsyncSession = Depends(get_async_session),
    ):
        record = TaskRecord(**task.model_dump())
        session.add(record)
        return record  # Auto-committed on yield exit
    ```
  * [get_managed_session()](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/session.py#L242): Async context manager (`@asynccontextmanager`) providing identical commit/rollback/close semantics for background worker tasks, cron scripts, and agent loops.

---

### High-Performance Caching & Shared Agent Memory (`src/db/redis_client.py`)

* **File Location:** [`src/db/redis_client.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py)
* **Architecture Role:** Async client wrapper over `redis.asyncio` with connection pooling. Provides namespace isolation for shared cross-agent memory, user session caching, and atomic sliding-window rate limiting.
* **Component Walkthrough:**
  * [init_redis()](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L411): Configures an async `ConnectionPool` with `max_connections = POSTGRES_POOL_SIZE * 2`, 5.0-second socket connect/read timeouts, and automatic retry on timeout (`retry_on_timeout=True`). Verifies connectivity on startup via PING.
  * [RedisClient](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L59) Methods:
    * *Basic Key/Value with TTL:* [get](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L108), [set](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L123) (with `setex`), [delete](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L146), [exists](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L158), [expire](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L163), [ttl](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L168).
    * *JSON Serialization:* [get_json](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L182) and [set_json](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L204) handle serialization and deserialization of complex dictionaries and lists with fallback error handling.
    * *Atomic Counters & Sliding-Window Rate Limiting:* [incr_with_ttl(key, ttl)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L266) uses a Redis pipeline to atomically increment a counter and inspect its current TTL. If the key was newly created (`ttl == -1`), it sets the expiration window, providing atomic sliding-window rate limiting.
    * *Rate Limit Evaluation:* [check_rate_limit(identifier, max_requests, window_seconds)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L373) returns `(is_allowed: bool, current_count: int)` using key prefixes (`devagent:ratelimit:`).
    * *Shared Agent Memory:* [set_shared_memory(task_id, key, value)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L300) and [get_shared_memory(task_id, key)](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L324) isolate cross-agent context under keys formatted as `devagent:memory:{task_id}:{key}` with default 24-hour expiration.
    * *Session Management:* [set_session](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L346), [get_session](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L358), and [delete_session](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L364) store conversation state under `devagent:session:{session_id}`.

---

### Unified Package Facades (`src/models/__init__.py` & `src/db/__init__.py`)

To prevent circular imports and simplify import statements, Phase 2 exposes clean package interfaces:

* **[`src/models/__init__.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/__init__.py):**
  ```python
  from src.models import (
      TaskCreate, TaskResponse, SubTaskResponse, TaskResult,  # Pydantic Schemas
      AgentState, OrchestratorState, create_agent_state,       # LangGraph States
      Base, TaskRecord, SubTaskRecord, ExecutionLog, AgentMetric # SQLAlchemy ORM
  )
  ```
* **[`src/db/__init__.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/__init__.py):**
  ```python
  from src.db import (
      init_db, close_db, get_async_session, get_managed_session,  # PostgreSQL
      init_redis, close_redis, get_redis_client, RedisClient       # Redis
  )
  ```

---

### Production Safeguards & Architectural Invariants

| Risk / Failure Mode | Mitigating Architecture & Safeguard | Implementation Location |
|:---|:---|:---|
| **Infinite LLM Execution Loops** | Bounded iteration ceilings (`iteration_count >= max_iterations` where `max_iterations=10`). If breached, `should_continue` is forced to `False`, forcing the agent out of the ReAct cycle. | [`src/models/state.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L146) |
| **State Context Overwrite** | Append-only reducers (`Annotated[list, operator.add]`) on `messages`, `tool_calls`, `subtask_results`, and `completed_subtasks`. Node state emissions are concatenated rather than overwriting history. | [`src/models/state.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L133) |
| **Missing State KeyErrors** | Factory functions (`create_agent_state`, `create_orchestrator_state`) initialize state instances with complete zero-value defaults for all expected fields. | [`src/models/state.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L301) |
| **Input Injection & Dirty Data** | Whitespace normalization validator (`clean_description`) collapses whitespace, strips leading/trailing spaces, and enforces string length boundaries (10 to 10,000 characters). | [`src/models/schemas.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L122) |
| **API Secret Leakage** | All credentials use Pydantic's `SecretStr` type, preventing plain-text values from printing in logs, exceptions, or JSON dumps. | [`src/config/settings.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/settings.py#L73) |
| **Orphaned Database Records** | Foreign key constraints enforce `ondelete="CASCADE"`. Deleting a parent `TaskRecord` automatically purges child subtasks, execution logs, and metrics. | [`src/models/database.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/database.py#L274) |
| **Stale Database Connections** | Pre-ping verification (`pool_pre_ping=True`) verifies socket health before issuing queries, and `pool_recycle=3600` recycles connections hourly. | [`src/db/session.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/session.py#L80) |
| **Redis Key Collisions** | Enforced namespace prefixing (`devagent:memory:`, `devagent:session:`, `devagent:ratelimit:`). | [`src/db/redis_client.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/db/redis_client.py#L39) |
| **Financial Overruns** | Dynamic token usage validation and per-call tracking in `AgentMetric`, with alert thresholds configured in `COST_ALERT_THRESHOLD_USD`. | [`src/config/settings.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/settings.py#L190) |

---

## 4. Phase 3 Deep-Dive: Core Orchestration Engine & Agent Framework

Phase 3 introduces the autonomous cognitive core of DevAgent. Building directly upon the infrastructure of Phase 1 and the data contracts and persistence engines of Phase 2, Phase 3 implements the active execution loop: multi-provider LLM abstraction with native failover, token and cost accounting, tool abstraction, bounded ReAct agent loops, topological task decomposition, concurrent dependency-aware dispatching, validation gates, and consensus-driven synthesis.

```
       ┌────────────────────────────────────────────────────────┐
       │             User Objective: TaskCreate                 │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │       Planner Node (LLM + Strict DAG Validation)       │
       │     - Decomposes into ordered SubTasks (UUIDs)         │
       │     - DFS Cycle Detection (visiting/visited sets)      │
       │     - Persists SubTaskRecords to PostgreSQL            │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │   Dispatcher Node (Topological Concurrent Scheduler)   │
       │     - Resolves unblocked DAG tiers iteratively         │
       │     - Concurrency throttling (asyncio.Semaphore)       │
       │     - Injects shared context from predecessor tasks    │
       │     - Self-healing retry loop (AGENT_MAX_RETRIES)      │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
       ┌──────────────────────┐        ┌──────────────────────┐
       │ Specialized Agent 1  │        │ Specialized Agent 2  │
       │ (ReAct State Machine)│        │ (ReAct State Machine)│
       │  reason ⇄ act ⇄ fin  │        │  reason ⇄ act ⇄ fin  │
       └──────────┬───────────┘        └──────────┬───────────┘
                  │                               │
                  └───────────────┬───────────────┘
                                  │ SubTaskResults
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │        Validator Node (Schema & Quality Gate)          │
       │     - Inspects SubTaskResult models and confidence     │
       │     - Verifies non-empty output and error flags        │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
         Valid    ▼                               ▼   Invalid / Retry Exhausted
       ┌──────────────────────┐        ┌──────────────────────┐
       │   Synthesizer Node   │        │  Error Handler Node  │
       │ - Weighted Confidence│        │ - Consolidates Errors│
       │ - Source Deduplication│       │ - Sets status=FAILED │
       │ - Emits TaskResult   │        │ - Audit Logging      │
       └──────────┬───────────┘        └──────────┬───────────┘
                  │                               │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │       OrchestratorEngine (TaskResponse Emission)       │
       │     - Persists completed TaskRecord to PostgreSQL      │
       │     - Enforces global timeout (ORCHESTRATOR_TIMEOUT)   │
       └────────────────────────────────────────────────────────┘
```

---

### Multi-Provider LLM Abstraction & Automatic Failover (`src/llm/`)

* **File Location:** [`src/llm/factory.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/factory.py) & [`src/llm/__init__.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/__init__.py)
* **Architecture Role:** Serves as the single, centralized gateway to all Large Language Model providers. Decouples the agent framework from concrete vendor SDKs, provides lazy runtime imports to minimize memory overhead, and orchestrates automatic model failover if the primary provider experiences outages, timeouts, or rate limits.
* **Component Walkthrough:**

| Function / Component | Signature & Parameters | Architectural Role & Implementation Details |
|:---|:---|:---|
| [`create_chat_model`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/factory.py#L18) | `provider: LLMProvider \| str, model: str, temperature: float \| None = None, max_tokens: int \| None = None, **kwargs: Any) -> Any` | Dynamic chat model factory. Performs **lazy SDK loading** (`langchain_openai`, `langchain_anthropic`, `langchain_google_genai`) so unused provider libraries are never imported into process memory. Retrieves secrets via `SecretStr.get_secret_value()`, injects `settings.LLM_REQUEST_TIMEOUT`, and returns an initialized LangChain `BaseChatModel`. |
| [`get_primary_llm`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/factory.py#L81) | `(**kwargs: Any) -> Any` | Convenience helper that instantiates the active primary model specified by `settings.LLM_PROVIDER` and `settings.LLM_MODEL`. |
| [`get_fallback_llm`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/factory.py#L86) | `(**kwargs: Any) -> Any \| None` | Instantiates the secondary failover model using `settings.LLM_FALLBACK_PROVIDER`, `settings.LLM_FALLBACK_MODEL`, and `settings.LLM_FALLBACK_API_KEY`. Returns `None` if failover is unconfigured. |
| [`get_llm_with_fallback`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/factory.py#L99) | `(**kwargs: Any) -> Any` | Wraps the primary LLM with LangChain's native `.with_fallbacks([fallback])`. If the primary provider encounters network timeouts, 429 rate limits, or 5xx outages, LangChain transparently catches the failure and falls back to the secondary model with zero dropped requests. |
| [`estimate_token_count`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/factory.py#L105) | `(text: str, model: str = "gpt-4o-mini") -> int` | High-speed local token estimator using `tiktoken`. If the model encoding is unrecognized or tiktoken fails, gracefully degrades to a conservative character heuristic: `max(1, (len(text) + 3) // 4)`. |
| [`calculate_cost`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/factory.py#L115) | `(prompt_tokens: int, completion_tokens: int, model: str) -> float` | Computes USD financial costs using the pricing matrix in [`LLM_COST_PER_MILLION_TOKENS`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L230). Features model prefix matching (e.g. matching `claude-3-5-sonnet-20241022` to `claude-3-5-sonnet`). |

---

### Async Token & Cost Accounting Engine (`src/llm/callbacks.py`)

* **File Location:** [`src/llm/callbacks.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/callbacks.py)
* **Architecture Role:** Provides non-blocking, multi-provider token consumption and financial cost auditing. Intercepts LLM completion events to capture real-time resource utilization without adding overhead to inference latency.
* **Component Walkthrough:**

```mermaid
flowchart LR
    LLM[LLM Provider Response] -->|on_llm_end| Callback[TokenTrackingCallback]
    Callback -->|Extract Usage| Inspector{Payload Format}
    Inspector -->|OpenAI| U1["llm_output['token_usage']"]
    Inspector -->|Google / Anthropic| U2["llm_output['usage_metadata']"]
    Inspector -->|Generational| U3["generation[0][0].message.usage_metadata"]
    U1 & U2 & U3 --> Accumulator[Accumulate prompt & completion tokens]
    Accumulator --> Snapshot[get_usage_snapshot]
    Snapshot --> Cost[calculate_cost: USD]
    Cost --> Metric[(PostgreSQL AgentMetric)]
```

* **Thread-Isolated Callback Lifecycle:**
  * Subclasses LangChain's `AsyncCallbackHandler`.
  * Instantiated per agent execution (`BaseAgent._callback = TokenTrackingCallback(...)`), guaranteeing that concurrent agent executions never cross-contaminate token counts.
  * Captures variations across LLM provider metadata formats: seamlessly parses `token_usage`, `usage_metadata`, or generational message metadata.
  * [`get_usage_snapshot()`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/callbacks.py#L30): Returns a normalized dictionary containing `prompt_tokens`, `completion_tokens`, `total_tokens`, and `cost_usd`.
  * [`reset()`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/callbacks.py#L40): Resets accumulator counters between task invocations.

---

### Tool Abstraction Layer & LangChain Adapter (`src/tools/`)

* **File Location:** [`src/tools/base.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/tools/base.py) & [`src/tools/__init__.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/tools/__init__.py)
* **Architecture Role:** Establishes the contract for internal agent tools and external Model Context Protocol (MCP) tool bindings. Provides thread-safe registration, agent-specific tool filtering, exception shielding, latency benchmarking, and seamless transformation into LangChain `StructuredTool` instances.
* **Component Walkthrough:**

| Component | Type | Architectural Purpose |
|:---|:---|:---|
| [`ToolResult`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/tools/base.py#L17) | `dataclass(slots=True)` | Standardized return envelope containing: `result: Any`, `error: str \| None`, `is_error: bool`, `duration_seconds: float`, and `metadata: dict[str, Any]`. Prevents unhandled exceptions from propagating into the agent loop. |
| [`BaseTool`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/tools/base.py#L26) | `ABC` | Abstract base class declaring: `name: ClassVar[str]`, `description: ClassVar[str]`, `args_schema: ClassVar[type[BaseModel] \| None]`, `supported_agents: ClassVar[set[AgentType]]`, and `source: ClassVar[MCPToolSource] = MCPToolSource.INTERNAL`. Requires implementing `async def execute(**kwargs) -> ToolResult`. |
| [`ToolRegistry`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/tools/base.py#L38) | Thread-Safe Singleton | Manages runtime tool discovery with `threading.RLock` synchronization. Provides `register(tool)`, `get(name)`, `list_tools()`, and `get_tools_for_agent(agent_type)` to enforce role-based tool isolation. |
| [`_run_tool`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/tools/base.py#L79) | `async function` | Protective execution wrapper. Benchmarks wall-clock execution time via `time.perf_counter()` and shields the agent ReAct loop by catching arbitrary runtime exceptions, converting them into `{is_error: True, error: str(exc)}` payloads. |
| [`tool_to_langchain`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/tools/base.py#L101) | Adapter Function | Converts any `BaseTool` into a LangChain `StructuredTool.from_function` with async coroutine binding, enabling transparent registration with `llm.bind_tools()`. |

---

### Base Agent ReAct Subgraph & Execution Loop (`src/agents/base.py`)

* **File Location:** [`src/agents/base.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/base.py) & [`src/agents/__init__.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/__init__.py)
* **Architecture Role:** Encapsulates the core autonomous reasoning engine. Implements the **Reason + Act (ReAct)** cognitive architecture as a compiled LangGraph `StateGraph(AgentState)` subgraph that is inherited and reused by all specialized agents.
* **The ReAct State Machine:**

```mermaid
stateDiagram-v2
    [*] --> START
    START --> reason: Initialize System & Subtask Prompt
    state reason {
        [*] --> LLM_Inference
        LLM_Inference --> Inspect_Tool_Calls
    }
    reason --> act: pending_tool_calls > 0 AND iteration < max_iterations
    reason --> finalize: pending_tool_calls == 0 OR iteration >= max_iterations
    state act {
        [*] --> Lookup_ToolRegistry
        Lookup_ToolRegistry --> Execute_Protected
        Execute_Protected --> Append_ToolMessage
    }
    act --> reason: Next Cognitive Turn
    state finalize {
        [*] --> Format_SubTaskResult
        Format_SubTaskResult --> Extract_Source_URLs
        Extract_Source_URLs --> Snapshot_Token_Metrics
    }
    finalize --> END
    END --> [*]
```

* **Node Execution Mechanics:**
  1. **Reason Node ([`_reason_node`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/base.py#L67)):**
     * Builds context-aware system messages by formatting role instructions with the subtask description and serialized `shared_context` from predecessor subtasks.
     * Invokes `_reasoning_llm` attached to `TokenTrackingCallback`.
     * Clamps returned tool calls to `AGENT_TOOL_CALL_MAX_PER_TURN` (default: 5) to prevent combinatorial explosion.
     * Increments `iteration_count` and updates `pending_tool_calls`.
  2. **Act Node ([`_act_node`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/base.py#L89)):**
     * Iterates over `pending_tool_calls`, resolves corresponding `BaseTool` from `ToolRegistry`, and safely executes via `_run_tool`.
     * Appends detailed audit entries to `tool_calls` state and creates LangChain `ToolMessage` instances for the LLM's conversation history.
     * Flushes `pending_tool_calls`.
  3. **Conditional Loop Guard ([`_should_continue`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/base.py#L112)):**
     * Checks `iteration_count >= max_iterations` (default: 10). If exceeded, forcibly halts the loop and routes to `finalize`.
     * If `pending_tool_calls` are present, routes to `act`.
     * If no tool calls are requested, routes to `finalize`.
  4. **Finalize Node ([`_finalize_node`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/base.py#L117)):**
     * Sanitizes final answer content and sets fallback error messages if unproduced.
     * Extracts cited URLs using regex matching (`r"https?://[^\s)]+"`).
     * Extracts token and cost snapshots from `TokenTrackingCallback`.
     * Emits a validated [SubTaskResult](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L442) payload with confidence scoring and execution status.
  5. **Invocation Entrypoint ([`invoke`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/base.py#L142)):**
     * Resets callback metrics, records wall-clock duration with `perf_counter()`, compiles and invokes the graph, and attaches `duration_seconds` to the result.

---

### Specialized Agent Registry & Factory (`src/agents/registry.py`)

* **File Location:** [`src/agents/registry.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/registry.py)
* **Architecture Role:** Provides a dynamic polymorphic factory that instantiates specialized agent personas with role-tuned system prompts, dedicated tool matrices, and isolated execution scopes.
* **Component Walkthrough:**

| Specialized Agent | Base Class | System Prompt Binding | Core Specialization & Tools |
|:---|:---|:---|:---|
| [`ResearchAgent`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/registry.py#L16) | [`BaseAgent`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/base.py#L21) | [`RESEARCH_AGENT_SYSTEM_PROMPT`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L263) | Web exploration, technical documentation ingestion, literature search, and source-attributed fact gathering. Automatically filters tools bound to `AgentType.RESEARCH`. |
| [`CodingAgent`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/registry.py#L21) | [`BaseAgent`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/base.py#L21) | [`CODING_AGENT_SYSTEM_PROMPT`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L275) | Polyglot code generation, software architecture, debugging, unit test creation, and sandboxed execution. Automatically filters tools bound to `AgentType.CODING`. |
| [`AnalysisAgent`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/registry.py#L26) | [`BaseAgent`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/base.py#L21) | [`ANALYSIS_AGENT_SYSTEM_PROMPT`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L287) | Quantitative benchmarking, database querying, statistical modeling, latency/cost profiling, and data visualization. Automatically filters tools bound to `AgentType.ANALYSIS`. |
| [`AgentRegistry`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/registry.py#L31) | Class-Level Factory | `create_agent(agent_type: AgentType \| str, **kwargs: Any) -> BaseAgent` | Resolves string or enum agent identifiers, verifies registration, and returns an initialized, isolated specialized agent instance. |

---

### Topological Task Decomposition & DAG Validation (`src/orchestrator/planner.py`)

* **File Location:** [`src/orchestrator/planner.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/planner.py) & [`src/orchestrator/__init__.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/__init__.py)
* **Architecture Role:** Acts as the cognitive entrypoint of the orchestration pipeline. Decomposes unstructured natural language objectives into a strictly validated Directed Acyclic Graph (DAG) of subtasks, establishes dependency edges, and persists the execution blueprint to PostgreSQL.
* **Component Walkthrough:**

```mermaid
flowchart TD
    UserReq[User Task Description] --> PlannerNode
    PlannerNode -->|with_structured_output| LLM[LLM Decomposition]
    LLM --> PlanSchema[PlanSchema: PlannedSubtasks]
    PlanSchema --> ValidateCount{Count <= max_subtasks?}
    ValidateCount -- No --> ErrLimit[Raise ValueError: Subtask Limit]
    ValidateCount -- Yes --> ValidateIndices{Dependencies < Current Index?}
    ValidateIndices -- No --> ErrDep[Raise ValueError: Non-preceding Dependency]
    ValidateIndices -- Yes --> DFS[DFS Cycle Detection: visiting / visited]
    DFS -- Cycle Detected --> ErrCycle[Raise ValueError: Circular Dependency]
    DFS -- Acyclic --> UUIDMapping[Translate Indexes to UUIDs]
    UUIDMapping --> PersistDB[(INSERT INTO subtasks)]
    PersistDB --> ReturnState[Return OrchestratorState: EXECUTING]
```

* **Structured Planning Contracts:**
  * [`PlannedSubtask(BaseModel)`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/planner.py#L19): Defines `description: str`, `agent_type: AgentType`, `order: int`, `dependencies: list[int]` (zero-based integer indices of prerequisite subtasks), and `tools_required: list[str]`.
  * [`PlanSchema(BaseModel)`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/planner.py#L29): Wraps `subtasks: list[PlannedSubtask]` and `reasoning: str`.
* **Topological Cycle Detection Algorithm ([`_validate_dag`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/planner.py#L40)):**
  * Constructs an adjacency list representing the dependency graph.
  * Ensures all declared dependency IDs exist in the generated subtask set.
  * Executes a recursive Depth-First Search (DFS) utilizing two tracking sets: `visiting` (current branch exploration) and `visited` (fully explored nodes). If a node in `visiting` is re-encountered, it proves a directed cycle exists and immediately rejects the plan with a `ValueError`.
* **UUID Translation & State Materialization:**
  * Converts integer dependencies (`item.dependencies: [0]`) into deterministic UUID strings.
  * Populates `subtask_states` dictionary with initialized `SubTaskStatus.PENDING` states.
  * Sets `status = TaskStatus.EXECUTING` and queues `pending_subtasks`.
* **Relational Persistence ([`_persist_plan`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/planner.py#L104)):**
  * Inserts [SubTaskRecord](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/database.py#L292) instances into PostgreSQL via async connection pool. Gracefully catches `RuntimeError` if the database session is not started, allowing offline unit testing without a live database.

---

### Dependency-Aware Concurrent Dispatcher (`src/orchestrator/dispatcher.py`)

* **File Location:** [`src/orchestrator/dispatcher.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/dispatcher.py)
* **Architecture Role:** Serves as the high-throughput DAG scheduler. Evaluates subtask readiness, manages parallel agent executions under strict semaphore concurrency limits, injects cross-agent shared memory context, and drives an in-place self-healing retry engine.
* **Component Walkthrough:**

```mermaid
flowchart TD
    PendingQueue[Pending Subtasks Queue] --> Resolver[_resolve_ready_subtasks]
    Resolver --> CheckReady{Any Subtasks Ready?}
    CheckReady -- No & Pending > 0 --> Deadlock[Dependency Deadlock: Mark Failed]
    CheckReady -- Yes --> ConcurrencyGate[Acquire asyncio.Semaphore]
    ConcurrencyGate --> ContextInject[Inject shared_context from Predecessors]
    ContextInject --> Gather[asyncio.gather Parallel Executions]
    Gather --> EvaluateOutcome{Agent Succeeded?}
    EvaluateOutcome -- Yes --> Success[Mark COMPLETED, Append Results, Persist DB]
    Success --> CheckRemaining{Pending Queue Empty?}
    EvaluateOutcome -- No --> CheckRetries{retry_count <= AGENT_MAX_RETRIES?}
    CheckRetries -- Yes --> ReQueue[Increment retry_count, Re-queue PENDING]
    CheckRetries -- No --> TerminalFail[Mark FAILED, Append failed_subtasks, Persist DB]
    ReQueue --> CheckRemaining
    TerminalFail --> CheckRemaining
    CheckRemaining -- No --> Resolver
    CheckRemaining -- Yes --> ReturnOutputs[Return OrchestratorState]
```

* **Core Dispatching Mechanics:**
  1. **Topological Readiness Resolution ([`_resolve_ready_subtasks`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/dispatcher.py#L23)):**
     * Scans `pending_subtasks` for items whose `dependencies` are a subset of `completed_subtasks`.
     * Unblocks independent tasks at the current topological depth simultaneously.
  2. **Cross-Agent Shared Context Injection ([`_shared_context`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/dispatcher.py#L32)):**
     * Downstream agents (e.g. Coding Agent) automatically receive the textual outputs produced by their prerequisite subtasks (e.g. Research Agent) via `shared_context`, enabling rich multi-agent synthesis without global state pollution.
  3. **Concurrency Throttling ([`asyncio.Semaphore`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/dispatcher.py#L64)):**
     * Limits concurrent agent invocations to `settings.AGENT_MAX_CONCURRENCY` (default: 5), protecting system resources and external API rate limits.
  4. **Parallel Execution Engine ([`asyncio.gather`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/dispatcher.py#L81)):**
     * Executes all ready subtasks concurrently using `return_exceptions=True` to prevent a single failure from aborting sibling tasks.
  5. **In-Place Self-Healing Retry Loop:**
     * Intercepts agent failures and exceptions.
     * Increments `retry_count`. If `retry_count <= settings.AGENT_MAX_RETRIES` (default: 3), resets status to `PENDING` and re-queues for execution.
     * If retries are exhausted, sets status to `FAILED`, appends to `failed_subtasks`, and cascades failure down uncompleted dependent branches.
  6. **Relational Persistence ([`_persist_outcome`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/dispatcher.py#L117)):**
     * Updates PostgreSQL `SubTaskRecord` with final status and result JSON.
     * Inserts an [AgentMetric](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/database.py#L504) record capturing token counts, cost in USD, and duration.
     * Logs an [ExecutionLog](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/database.py#L427) audit entry (`agent_completed` or `agent_failed`).

---

### Top-Level Orchestration Pipeline & Graph Engine (`src/orchestrator/engine.py`)

* **File Location:** [`src/orchestrator/engine.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/engine.py) & [`src/orchestrator/__init__.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/__init__.py)
* **Architecture Role:** The master LangGraph state machine compiling the entire multi-agent lifecycle: Planner $\rightarrow$ Dispatcher $\rightarrow$ Validator $\rightarrow$ Synthesizer. Exposes the public async API for executing tasks with timeout protection and database synchronization.
* **The Master StateGraph Architecture:**

```mermaid
flowchart TD
    START([START]) --> Planner[planner: PlannerNode.plan_task]
    Planner --> Dispatcher[dispatcher: DispatcherNode.dispatch_subtasks]
    
    Dispatcher --> after_dispatch{failed_subtasks empty?}
    after_dispatch -- No --> ErrorHandler[error_handler: Consolidate Errors]
    after_dispatch -- Yes --> Validator[validator: Verify Schemas & Confidence]
    
    Validator --> after_validation{validation_errors empty?}
    after_validation -- No --> ErrorHandler
    after_validation -- Yes --> Synthesizer[synthesizer: Merge & Weight Confidence]
    
    Synthesizer --> END([END: TaskStatus.COMPLETED])
    ErrorHandler --> END_FAIL([END: TaskStatus.FAILED])
```

* **Node & Edge Specifications:**
  * **Planner Node (`planner`):** Calls [`PlannerNode.plan_task`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/planner.py#L61) to decompose the request into a validated subtask DAG.
  * **Dispatcher Node (`dispatcher`):** Calls [`DispatcherNode.dispatch_subtasks`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/dispatcher.py#L57) to execute unblocked subtasks concurrently across specialized agents.
  * **Validator Node ([`validator_node`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/engine.py#L25)):**
    * Verifies that `failed_subtasks` is empty.
    * Ensures `subtask_results` contains valid entries.
    * Re-validates every subtask output against [SubTaskResult](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L442), enforcing non-empty string content and positive confidence scores.
  * **Synthesizer Node ([`synthesizer_node`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/engine.py#L40)):**
    * Computes a **token-weighted overall confidence score**:
      $$\text{overall\_confidence} = \frac{\sum_{i} (\text{result}_i.\text{confidence} \times \max(\text{result}_i.\text{token\_count}, 1))}{\sum_{i} \max(\text{result}_i.\text{token\_count}, 1)}$$
    * Deduplicates cited source URLs across all agents: `list(dict.fromkeys(...))`.
    * Compiles the consolidated [TaskResult](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L479) payload with aggregated tokens, costs, and output.
    * Sets `status = TaskStatus.COMPLETED`.
  * **Error Handler Node ([`error_handler_node`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/engine.py#L62)):**
    * Consolidates validation failures or execution exceptions into a unified error trace.
    * Sets `status = TaskStatus.FAILED`.
* **Public Service Engine ([`OrchestratorEngine`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/engine.py#L95)):**
  * `async run_task(task_create: TaskCreate) -> TaskResponse`:
    * Initializes top-level state via `create_orchestrator_state()`.
    * Creates an initial `TaskRecord` in PostgreSQL with `status="pending"`.
    * Enforces a hard global execution timeout: `asyncio.wait_for(..., timeout=settings.ORCHESTRATOR_TIMEOUT)` (default: 300s). Transitions to `TaskStatus.TIMED_OUT` if deadline is exceeded.
    * Updates `TaskRecord` with final status, token sums, cost in USD, and duration in seconds.
    * Emits a comprehensive [TaskResponse](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L152) payload to the caller.

---

### Phase 3 Production Safeguards & Resilience Matrix

| Risk / Failure Mode | Mitigating Architecture & Safeguard | Implementation Location |
|:---|:---|:---|
| **LLM Provider Outage / 429 / 5xx** | Multi-provider fallback chain via `.with_fallbacks([fallback])`. Seamlessly shifts execution from primary (e.g. Gemini) to secondary (e.g. OpenAI) with zero downtime. | [`src/llm/factory.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/factory.py#L99) |
| **Circular Dependencies in Subtask DAG** | Recursive Depth-First Search cycle detection with `visiting` and `visited` sets during planning. Rejects cyclical graphs before any agent execution begins. | [`src/orchestrator/planner.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/planner.py#L40) |
| **Subtask Dependency Deadlocks** | Dispatcher verifies ready subtasks at each DAG tier. If pending subtasks exist but none can be unblocked, terminates deadlock and flags orphaned tasks as failed. | [`src/orchestrator/dispatcher.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/dispatcher.py#L74) |
| **Transient Agent / Network Failure** | In-place retry loop re-queuing failed subtasks up to `settings.AGENT_MAX_RETRIES` (default: 3) before flagging terminal failure. | [`src/orchestrator/dispatcher.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/dispatcher.py#L97) |
| **API Rate Limit & Concurrency Starvation** | Asynchronous semaphore concurrency gate (`asyncio.Semaphore(settings.AGENT_MAX_CONCURRENCY)`). Caps parallel agent executions to safe thresholds. | [`src/orchestrator/dispatcher.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/dispatcher.py#L64) |
| **Runaway Agent ReAct Loops** | Bounded iteration ceilings (`iteration_count >= max_iterations`). Forcibly transitions agents to `finalize` node if ceiling (default: 10) is breached. | [`src/agents/base.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/agents/base.py#L113) |
| **Tool Execution Exception Crashes** | Exception-shielded execution wrapper `_run_tool` catching arbitrary runtime errors, recording execution duration, and returning structured error payloads. | [`src/tools/base.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/tools/base.py#L79) |
| **Cross-Agent Token Accounting Race Conditions** | Dedicated, thread-isolated `TokenTrackingCallback` instances attached exclusively to individual agent invocations. Eliminates concurrent memory corruption. | [`src/llm/callbacks.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/llm/callbacks.py#L12) |
| **Runaway Task Execution Timeouts** | Global pipeline timeout wrapper `asyncio.wait_for(timeout=settings.ORCHESTRATOR_TIMEOUT)`. Automatically transitions zombie tasks to `TIMED_OUT`. | [`src/orchestrator/engine.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/engine.py#L116) |
| **Malformed Subtask Output Hallucinations** | Validation gate verifying all agent outputs against `SubTaskResult` Pydantic schemas, checking non-empty text and positive confidence thresholds. | [`src/orchestrator/engine.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/orchestrator/engine.py#L25) |

---

## 5. Interactive Execution Trace & Metric Lifecycle

### End-to-End Execution Walkthrough: "Research & Benchmark Vector Stores"

To illustrate how data transforms across all layers, consider a sample user request:
> *"Research Pinecone vs Qdrant vs pgvector for real-time agent memory, generate integration code for the best option, and benchmark latency vs cost tradeoffs."*

```mermaid
sequenceDiagram
    autonumber
    actor User as Client Application
    participant API as FastAPI Gateway
    participant Orch as LangGraph Orchestrator
    participant Redis as Redis Cache / Memory
    participant Research as Research Agent
    participant Coding as Coding Agent
    participant Analysis as Analysis Agent
    participant DB as PostgreSQL 16+

    User->>API: POST /api/v1/tasks (TaskCreate)
    API->>DB: INSERT INTO tasks (TaskRecord, status='pending')
    API->>Orch: create_orchestrator_state(task_id, description)

    rect rgb(240, 248, 255)
        note over Orch: 1. PLANNING PHASE
        Orch->>Orch: PlannerNode runs LLM decomposition
        Orch->>DB: INSERT INTO subtasks (3 SubTaskRecords)
        Orch->>Orch: Populate plan & subtask_states (DAG)
    end

    rect rgb(255, 250, 240)
        note over Orch, Research: 2. DISPATCH & RESEARCH (Order 0)
        Orch->>Research: Dispatch Subtask 1 (AgentState)
        Research->>Research: ReAct Loop (Tavily search)
        Research->>Redis: set_shared_memory("vector_store_findings", data)
        Research->>DB: INSERT INTO agent_metrics (tokens, cost)
        Research-->>Orch: Return SubTaskResult (Output, confidence=0.95)
    end

    rect rgb(240, 255, 240)
        note over Orch, Analysis: 3. PARALLEL EXECUTION (Order 1)
        Orch->>Coding: Dispatch Subtask 2 (Reads shared memory)
        Orch->>Analysis: Dispatch Subtask 3 (Reads shared memory)
        Coding->>Coding: Generate & test connection code
        Analysis->>Analysis: Calculate latency vs cost tradeoffs
        Coding-->>Orch: Return SubTaskResult (Python snippet, confidence=0.98)
        Analysis-->>Orch: Return SubTaskResult (Metrics table, confidence=0.92)
    end

    rect rgb(255, 240, 245)
        note over Orch: 4. VALIDATION & SYNTHESIS
        Orch->>Orch: ValidatorNode verifies schema compliance
        Orch->>Orch: SynthesizerNode merges outputs (TaskResult)
        Orch->>DB: UPDATE tasks (status='completed', result, total_cost)
    end

    Orch-->>API: TaskResponse
    API-->>User: 200 OK (TaskResponse JSON)
```

---

### Step-by-Step State Mutation Trace

#### Step 1: Ingestion & Validation (`TaskCreate` $\rightarrow$ `TaskRecord`)
The client submits a JSON payload to `POST /api/v1/tasks`. [TaskCreate](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L86) validates that the description exceeds 10 characters and normalizes whitespace:
```python
# Ingested Schema
task_input = TaskCreate(
    description="Research Pinecone vs Qdrant vs pgvector for real-time agent memory...",
    priority=Priority.HIGH,
    metadata={"requester": "infra-team", "budget_limit_usd": 5.0}
)

# Persisted to DB
task_record = TaskRecord(
    id=uuid.uuid4(),
    description=task_input.description,
    priority=task_input.priority.value,
    status=TaskStatus.PENDING.value,
    metadata_=task_input.metadata
)
```

#### Step 2: Orchestrator Graph Initialization (`OrchestratorState`)
The orchestrator initializes top-level state via [create_orchestrator_state](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L344):
```python
state: OrchestratorState = {
    "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "task_description": "Research Pinecone vs Qdrant vs pgvector...",
    "status": "pending",
    "plan": [],
    "subtask_states": {},
    "pending_subtasks": [],
    "active_subtasks": [],
    "completed_subtasks": [],
    "subtask_results": [],
    "total_tokens": 0,
    "total_cost_usd": 0.0,
    ...
}
```

#### Step 3: Topological Decomposition (`PlannerNode`)
The planner breaks the request into three subtasks with dependency edges:
* **Subtask 1 (Order 0, No Prereqs):** `agent_type="research"` $\rightarrow$ "Gather specifications, pricing, and latency benchmarks for Pinecone, Qdrant, and pgvector."
* **Subtask 2 (Order 1, Depends on Subtask 1):** `agent_type="coding"` $\rightarrow$ "Write an async Python wrapper for the recommended store."
* **Subtask 3 (Order 1, Depends on Subtask 1):** `agent_type="analysis"` $\rightarrow$ "Build a tradeoff matrix comparing indexing speed, query latency, and hosting costs."

`pending_subtasks` queues Subtasks 2 and 3, while Subtask 1 transitions to `active_subtasks`.

#### Step 4: Specialized Agent ReAct Execution (`AgentState`)
The orchestrator instantiates [create_agent_state](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/state.py#L301) for the Research Agent:
```python
agent_state: AgentState = {
    "agent_type": "research",
    "subtask_id": "subtask-001",
    "iteration_count": 0,
    "max_iterations": 10,
    "should_continue": True,
    "messages": [
        {"role": "system", "content": RESEARCH_AGENT_SYSTEM_PROMPT},
        {"role": "human", "content": "Gather specifications..."}
    ],
    "tool_calls": []
}
```
* **Iteration 1:** The LLM issues a [ToolCallRequest](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L334) for `web_search(query="pinecone vs qdrant vs pgvector benchmarks 2024")`.
* **Tool Execution:** The tool returns a [ToolCallResponse](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L360) with search results. LangGraph's `Annotated[list, operator.add]` appends the message and tool response without overwriting conversation history.
* **Iteration 2:** The LLM synthesizes findings, sets `should_continue = False`, and yields [SubTaskResult](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L442).
* **Context Staging:** The Research Agent stores findings in shared memory via `redis_client.set_shared_memory(task_id, "research_findings", raw_data)`.

#### Step 5: Parallel Downstream Dispatching
Subtask 1 completes, unblocking dependencies for Subtasks 2 and 3. The Dispatcher routes them in parallel:
* **Coding Agent:** Pulls `research_findings` from Redis and generates integration code using the Coding sandbox.
* **Analysis Agent:** Pulls `research_findings` from Redis, calculates cost-per-query curves, and builds the tradeoff matrix.

Both agents return their [SubTaskResult](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L442) payloads, appending them to `OrchestratorState["subtask_results"]`.

#### Step 6: Validation, Consensus & Synthesis (`TaskResult` $\rightarrow$ `TaskResponse`)
* The Validator Node verifies schema compliance and confirms confidence thresholds (`0.95`, `0.98`, `0.92`).
* The Synthesizer Node computes an overall weighted confidence score of `0.95` and compiles the consolidated [TaskResult](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L479).
* The orchestrator updates `TaskRecord` in PostgreSQL with `status="completed"`, stores the result JSON, and returns [TaskResponse](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/schemas.py#L152) to the client.

---

### Token, Latency, and Financial Cost Lifecycle

DevAgent tracks token consumption, latency, and estimated financial costs across all agent interactions:

```
[ LLM Provider API Response ]
            │
            ▼
[ TokenUsage Record Extracted ]
  ├─ prompt_tokens: 1,420
  ├─ completion_tokens: 380
  ├─ total_tokens: 1,800 (auto-computed)
  └─ duration: 1.84s
            │
            ▼
[ Financial Cost Calculation ]
  Formula: (prompt_tokens * input_rate + completion_tokens * output_rate) / 1,000,000
  Gemini-1.5-Flash: (1420 * $0.075 + 380 * $0.30) / 1,000,000 = $0.0002205 USD
            │
            ▼
[ Relational Persistence & Aggregation ]
  1. INSERT INTO agent_metrics (subtask_id, tokens, cost, duration)
  2. Aggregated to SubTaskRecord.token_usage
  3. Rolled up into TaskRecord.total_tokens, total_cost_usd, and duration_seconds
```

* **Pricing Source:** Token rates are drawn from the centralized pricing matrix in [`src/config/constants.py`](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/config/constants.py#L230).
* **Audit Trail:** Every LLM interaction is persisted as an [AgentMetric](file:///c:/Users/Teja/Downloads/Multi-Agent-Orchestration/src/models/database.py#L504) record linked to both the task and subtask.
* **Budget Enforcement:** If cumulative cost exceeds `COST_ALERT_THRESHOLD_USD` (default: $50.00), the system logs warning alerts and can trigger webhooks.

---

## 6. Repository Structure

```
Multi-Agent-Orchestration/
├── .env.example               # Complete environment variable blueprint (11 subsystems)
├── .gitignore                 # Excludes .env, caches, venv, and build artifacts
├── Makefile                   # Unified developer shortcuts (build, run, test, lint, docker)
├── pyproject.toml             # PEP 621 dependencies, tool configs (Ruff, Mypy, Pytest)
├── README.md                  # Comprehensive system documentation
└── src/
    ├── __init__.py            # Application metadata (__version__ = "0.1.0")
    ├── agents/                # Bounded ReAct agent subgraph & specialized personas
    │   ├── __init__.py        # Re-exports BaseAgent, AgentRegistry, Research/Coding/Analysis agents
    │   ├── base.py            # LangGraph ReAct subgraph (reason -> act -> finalize loop)
    │   └── registry.py        # Factory mapping AgentType to specialized agent instances
    ├── config/                # Centralized configuration & constants
    │   ├── __init__.py        # Exports get_settings, constants, and enums
    │   ├── constants.py       # Enums (AgentType, TaskStatus), prompts, pricing tables
    │   └── settings.py        # Pydantic BaseSettings, SecretStr validation, URL generators
    ├── db/                    # Persistence engine & connection lifecycle
    │   ├── __init__.py        # Exports init_db, get_async_session, get_redis_client
    │   ├── redis_client.py    # Async Redis client, connection pool, shared memory, rate limiting
    │   └── session.py         # Async PostgreSQL engine, connection pool, session factories
    ├── llm/                   # Multi-provider LLM abstraction & metric instrumentation
    │   ├── __init__.py        # Re-exports factory methods, token tracking callback, cost calculator
    │   ├── callbacks.py       # Async TokenTrackingCallback intercepting usage across providers
    │   └── factory.py         # Chat model factory (Google/OpenAI/Anthropic/Azure) with failover
    ├── models/                # Unified data models & state architecture
    │   ├── __init__.py        # Clean exports for schemas, states, and ORM entities
    │   ├── database.py        # SQLAlchemy 2.0 ORM models (TaskRecord, SubTaskRecord, etc.)
    │   ├── schemas.py         # Pydantic v2 data contracts (TaskCreate, TaskResponse, etc.)
    │   └── state.py           # LangGraph TypedDict states with append-only reducers
    ├── orchestrator/          # Top-level DAG orchestration & scheduler pipeline
    │   ├── __init__.py        # Re-exports OrchestratorEngine, PlannerNode, build_orchestrator_graph
    │   ├── dispatcher.py      # Dependency-aware concurrent scheduler with retry loop & semaphore
    │   ├── engine.py          # Master LangGraph pipeline (Planner -> Dispatcher -> Validator -> Synthesizer)
    │   └── planner.py         # Structured LLM task decomposition with acyclic DAG validation
    └── tools/                 # Tool contracts and LangChain integration adapter
        ├── __init__.py        # Re-exports BaseTool, ToolRegistry, ToolResult, tool_to_langchain
        └── base.py            # Abstract BaseTool, thread-safe ToolRegistry, StructuredTool adapter
```

---

## 7. Getting Started

### Prerequisites
* Python 3.11 or higher
* Docker & Docker Compose (for local PostgreSQL and Redis)
* Make utility (`scoop install make` on Windows, or use `choco install make`)

### Quick Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/TEJAMOGADALA/Multi-Agent-Orchestration.git
   cd Multi-Agent-Orchestration
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and supply your API keys (e.g., GOOGLE_API_KEY, OPENAI_API_KEY)
   ```

3. **Install dependencies:**
   ```bash
   make install-dev
   ```

4. **Start database and cache infrastructure:**
   ```bash
   make docker-up
   ```

5. **Run code quality and type verification:**
   ```bash
   make check
   ```

6. **Run test suite:**
   ```bash
   make test
   ```