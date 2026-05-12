# Project Astra — Development Roadmap

> Phased plan to systematically build toward the full specification while keeping each phase independently useful.
> Astra is being designed as a continuously usable assistant, not a giant unfinished research project.

---

## Current State Summary

**What's working (prototype-level):**

- ✅ Rust core: IPC server, event bus, SQLite logging, reducer, tool runner, Game Mode watcher
- ✅ Python orchestrator: agent loop, prompt construction, memory retrieval, LLM client, tool-call extraction
- ✅ HUD: Tauri + React overlay with glassmorphism UI, sends input, receives output
- ✅ Test suite: Rust unit tests, Python unit tests (with fake FAISS), E2E harness
- ✅ The full event flow works: HUD → core → orchestrator → LLM → tool → core → HUD

**What's incomplete or fragile:**

| Area | Problem | Severity |
|------|---------|----------|
| LLM output separation | Freeform LLM text mixed with executable intent — regex is a symptom, not the root cause | 🔴 Critical |
| Embeddings | `DummyEmbedder` — hash-based random vectors, not real semantic search | 🔴 Critical |
| No Intent Contract | Retries, replanning, and interruption will drift behavior without a stabilized intent object | 🔴 Critical |
| No canonical event schema | `EventEnvelope.data` is untyped `serde_json::Value` — schema drift between Rust/Python/HUD is inevitable | 🟡 High |
| Model routing | `route_task()` ignores task type, always returns same `LlamaClient` | 🟡 High |
| Hardcoded paths | Socket, DB, vault, toggle script — all baked into source | 🟡 High |
| HUD | Single response display, no conversation history, no streaming, no cancel | 🟡 High |
| Security model | Confirmation-first instead of capability-first; `CapabilityToken` defined but never used | 🟡 High |
| No conversation persistence | Replayability, debugging, recovery, regression testing all depend on preserved state | 🟡 High |
| Error handling | No retry logic, no fallback, no recovery — errors just get logged | 🟠 Medium |
| Logging | `print()` everywhere in Python, no structured logging | 🟠 Medium |
| No config system | Everything hardcoded, no `.env` or config file | 🟠 Medium |
| State machine | Spec defines 10 states, reducer only handles 4 events | 🟠 Medium |
| No execution context tracking | Replay is approximate reconstruction, not deterministic reproduction — model params, prompt versions, memory sets, tool versions are not captured | 🟠 Medium |
| No interruption semantics | No formal model for why execution stopped or whether it can resume — critical once background tasks, DAGs, and context awareness coexist | 🟠 Medium |
| No evaluation infrastructure | No golden traces, no replay, no regression suites | 🟠 Medium |
| No CI/CD | No workflows, no linting, no formatting config | 🟢 Low |

---

## Architectural Principles

These principles emerged from roadmap review and shape all phases below.

### AP-1: Intent Contracts Stabilize Behavior

The pipeline is not just `capture → classify → retrieve → decide → act`. Between classification and planning there is a missing stabilization layer: the **Intent Contract**.

```
IntentContract {
    objective,              // what the user wants
    constraints,            // what must not happen
    requires_tools,         // whether tool use is expected
    requires_confirmation,  // whether user approval is needed
    persistence_policy,     // should this interaction be memorized?
    expected_output_type,   // text, file, status, etc.
}
```

Without this, retries drift behavior, replanning loses the original goal, background tasks have no anchor, and interruption has no resumption point. The Intent Contract is the stable reference that all downstream execution must satisfy.

### AP-2: Capability-First, Not Confirmation-First

The mental model for tool authorization should be:

```
capability acquisition → temporary authorization → execution
```

Not:

```
danger_tier → confirmation → token
```

Confirmation is **one way** to obtain a capability — it is not the capability system itself. This distinction matters because it enables:

- Session-scoped permissions ("allow this terminal command category for 10 minutes")
- Trusted workflows that skip confirmation after initial approval
- Automation macros with pre-granted capabilities
- Project-scoped permission profiles
- Proactive Astra behavior with bounded authority

The capability system is the authorization layer. Confirmation dialogs are one UI for it.

### AP-3: Canonical Internal Message Schema

The biggest long-term maintainability risk is schema drift between Rust, Python, and the HUD. `EventEnvelope.data` is currently an untyped `serde_json::Value`. This must become typed before Phase 3.

**Rust side:**

```rust
enum EventPayload {
    UserInput(UserInputPayload),
    ToolRequest(ToolRequestPayload),
    ToolResult(ToolResultPayload),
    ToolRejected(ToolRejectedPayload),
    MemoryRetrieved(MemoryPayload),
    ConfirmationRequest(ConfirmationPayload),
    IntentContracted(IntentContractPayload),
    // ...
}
```

**Python side:**

```python
# Pydantic models mirroring the Rust enum variants
class UserInputPayload(BaseModel): ...
class ToolRequestPayload(BaseModel): ...
class ToolResultPayload(BaseModel): ...
# ...
```

Both sides must validate against the same schema. If a payload doesn't match, it is rejected — no "best effort parsing."

### AP-4: Structured Tool Channels, Not Regex Extraction

Regex parsing is a symptom. The deeper problem is **freeform LLM text mixed with executable intent**. Even with proper JSON extraction, you still face:

- Hallucinated tools (tool name that doesn't exist)
- Malformed arguments (wrong types, missing fields)
- Partial plans (LLM outputs half a tool call)
- Hidden assumptions (LLM assumes context not in the prompt)
- Implicit dependencies (tool B depends on tool A's output, but the LLM doesn't state this)

The long-term solution is **structured tool channels** — separating conversational text from executable intent at the generation level:

```
assistant text here
TOOL_CALL_START
{"tool_name": "run_shell", "args": {"cmd": "ls -la ~"}}
TOOL_CALL_END
```

Or eventually: grammar-constrained decoding that makes invalid tool calls syntactically impossible.

The roadmap progresses through three stages:
1. **Robust extraction** (Phase 1) — proper parser, schema validation, rejection feedback
2. **Delimited channels** (Phase 3) — explicit markers separating text from tool calls
3. **Constrained decoding** (Phase 6) — model-level guarantees

### AP-5: Single-Step Robustness Before Multi-Step Planning

Multi-step planning is where most assistant projects collapse — not technically, but architecturally. Once plans become mutable and stateful, you suddenly need:

- Dependency tracking
- Cancellation semantics
- Partial success semantics
- Rollback philosophy
- Resumability
- Retry isolation
- State snapshots

The progression must be:

1. **Single-step robustness** — every individual tool call is reliable, recoverable, and observable
2. **Linear plans** — ordered sequences of tool calls with result forwarding
3. **Branching DAGs** — conditional execution with dependency resolution

Do not jump directly to arbitrary DAG execution.

### AP-6: Deterministic Execution Boundaries

Replay exists. Event persistence exists. Schemas exist. But deterministic reproduction is still underspecified. Without explicit tracking of execution context, replay becomes **approximate historical reconstruction** instead of **actual deterministic replay**.

Every task and session must carry an `ExecutionContext`:

```
ExecutionContext {
    model_id,                    // which model generated the response
    temperature,                  // generation parameters used
    max_tokens,
    prompt_template_version,      // which prompt template was active
    retrieved_memory_ids,         // which memory chunks were injected
    tool_registry_version,        // which tools were available
    planner_version,              // which planner logic was used
    routing_decision,             // why this model/params was chosen
}
```

This becomes extremely valuable for regression analysis. If a planner regression is detected, you need to know whether the behavior change came from the model, the prompt, the memory set, the tool registry, or the planner logic itself. Without `ExecutionContext`, you're guessing.

**Attachment point**: `ExecutionContext` is attached to every task at creation time and to every session. It is immutable once set. If a retry or replan changes the context (e.g., different temperature), a new `ExecutionContext` is created and linked to the original.

### AP-7: Formal Interruption Semantics

Cancellation, resumption, and retries are mentioned throughout the spec, but there is no formal model for **why** execution stopped and **whether** it can resume. This becomes one of the hardest system problems once background tasks, DAGs, streaming, proactive execution, and context awareness coexist.

Interruption reasons must be explicit:

```
InterruptReason {
    user_cancelled,          // user explicitly stopped the task
    capability_revoked,      // authorization was withdrawn mid-execution
    dependency_failed,       // a prerequisite tool/step failed
    context_invalidated,     // the execution environment changed under the task
    timeout,                 // execution exceeded time budget
    system_suspend,          // Game Mode or similar system-level suspension
}
```

**Context invalidation** is the hardest case and deserves special attention. It occurs when:

- Active project changed (user switched terminals/repos)
- Clipboard changed (user copied new content)
- Git branch changed (user switched branches mid-task)
- File modified externally (user or another process edited a file the task depends on)

When context is invalidated, the system must decide: **should the plan continue?** The answer depends on the Intent Contract's constraints and the nature of the change. A file rename in an unrelated directory is ignorable; a branch switch that changes the file the task is operating on is not.

**Interruption handling rules**:

- `user_cancelled` → immediate halt, preserve partial progress, mark task cancelled
- `capability_revoked` → immediate halt, preserve partial progress, mark task awaiting re-authorization
- `dependency_failed` → halt downstream, preserve completed steps, offer replan
- `context_invalidated` → evaluate severity against Intent Contract; if constraints violated, halt and offer replan; if ignorable, continue with warning
- `timeout` → halt, preserve partial progress, mark task timed_out
- `system_suspend` → pause execution, preserve full state, resume on `system.resume`

This model becomes critical in Phase 5+ when context awareness makes context invalidation a real, frequent event.

---

## Phase 1: Foundation Hardening

> Make what exists actually reliable before building on top of it.

### 1.1 Config System (TOML)

**Why first**: Everything else (paths, model params, tool permissions) depends on configurable values.

- Create `~/.config/astra/config.toml` with sections: `[core]`, `[orchestrator]`, `[llm]`, `[memory]`, `[hud]`, `[security]`
- Move all hardcoded paths into config: socket path, DB path, vault path, toggle script path
- Rust core reads config on startup (add `toml` + `serde` crate)
- Python orchestrator reads same config file (add `tomli` for Python < 3.11, `tomllib` for 3.11+)
- HUD reads config for socket path
- **Fallback**: if config missing, use current hardcoded defaults (backward compatible)

**Key decisions**:

- Config file location: `~/.config/astra/config.toml` (XDG-compliant)
- Both Rust and Python read the same file — single source of truth

**Example config**:

```toml
[core]
socket_path = "/tmp/astra.sock"
db_path = "/tmp/astra.db"

[orchestrator]
vault_path = "/home/jperez/Astra/memories"
log_level = "INFO"

[llm]
server_url = "http://localhost:8080/v1"
default_max_tokens = 512
default_temperature = 0.7

[memory]
embedder_type = "sentence-transformers"  # or "dummy"
embedder_model = "all-MiniLM-L6-v2"
embedder_dim = 384
index_rebuild_on_start = false

[hud]
always_on_top = true

[security]
blocked_commands = ["rm -rf /", "mkfs", "dd if=/dev/zero"]
allowed_paths = ["/home/jperez", "/tmp"]
confirmation_timeout_secs = 30
```

### 1.2 Structured Logging (Python)

**Why before tool parsing and embeddings**: Once you begin replacing the parsing and memory systems, observability becomes essential. Without structured logs, debugging agent loops is miserable, retry behavior is opaque, and planner failures are hard to diagnose.

- Replace all `print()` in orchestrator with Python `logging` module
- Log levels: DEBUG for IPC messages, INFO for agent cycle steps, WARNING for parse failures, ERROR for LLM/tool errors
- Structured log format: timestamp, level, module, message, optional context dict
- Configurable log level in `config.toml`: `[orchestrator] log_level = "INFO"`
- Add Rust-side structured logging too (use `log` + `env_logger` crates)

### 1.3 Structured Tool Parsing (Kill the Regex)

**Why critical**: The current regex `re.search(r'\{.*\}', llm_response, re.DOTALL)` is the most fragile piece of the system. But the deeper issue is freeform LLM text mixed with executable intent (see AP-4). This phase delivers robust extraction; delimited channels come in Phase 3.

- Define a formal tool-call grammar in the prompt (the current JSON schema is fine, but extraction must be robust)
- Replace regex with a proper parser: extract the **last** JSON block containing `tool_name` + `args`, validate against the tool registry schema
- Add schema validation: check that `tool_name` exists in registry, that `args` match the `input_schema`
- Invalid tool calls → emit a `tool.rejected` event with a reason, feed back to the LLM as "that tool doesn't exist / args are wrong, try again"
- Handle edge cases: hallucinated tools, malformed arguments, partial plans, multiple JSON blocks
- **Tests**: expand `test_agent_cycle.py` with edge cases (multiple JSON blocks, malformed JSON, unknown tool names, missing required args, hallucinated tool names)

### 1.4 Conversation Persistence & Execution Context

**Why this early and not in Phase 3**: Conversation persistence is not UX polish — it is foundational infrastructure. Replayability, debugging, recovery, regression testing, and observability all depend on preserved conversational state. Without it, every agent loop is a black box.

- Add a `conversations` table to SQLite: session_id, role, content, timestamp, event_id
- Core logs every `ui.input` and `ui.output` event to this table
- On HUD reconnect, replay recent conversation from DB
- This becomes the foundation for evaluation infrastructure in Phase 3.5

**Execution Context tracking** (see AP-6): Without this, replay is approximate reconstruction, not deterministic reproduction. Every session and task must capture the conditions under which decisions were made.

- Add an `execution_contexts` table to SQLite: context_id, session_id, task_id, model_id, temperature, max_tokens, prompt_template_version, tool_registry_version, planner_version, routing_decision, created_at
- Add a `retrieved_memory_ids` table: context_id, memory_id, rank, distance_score
- The orchestrator emits an `execution.context_captured` event at the start of each agent cycle, containing the full `ExecutionContext`
- Core persists this alongside the conversation
- On replay (Phase 3.5), the `ExecutionContext` allows answering: "did this regression come from the model, the prompt, the memory set, or the planner?"

**Rust side:**

```rust
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct ExecutionContext {
    pub model_id: String,
    pub temperature: f32,
    pub max_tokens: u32,
    pub prompt_template_version: String,
    pub retrieved_memory_ids: Vec<String>,
    pub tool_registry_version: String,
    pub planner_version: String,
    pub routing_decision: String,
}
```

**Python side:**

```python
class ExecutionContext(BaseModel):
    model_id: str
    temperature: float
    max_tokens: int
    prompt_template_version: str
    retrieved_memory_ids: list[str]
    tool_registry_version: str
    planner_version: str
    routing_decision: str
```

### 1.5 Real Embeddings

**Why after logging and parsing**: You need observability in place before swapping out the memory system, because debugging embedding quality issues without logs is extremely painful.

- Add `sentence-transformers` as an orchestrator dependency
- Create `RealEmbedder` class using `all-MiniLM-L6-v2` (22MB, fast, good quality for local use)
- Make it configurable: `embedder.type = "dummy" | "sentence-transformers"`, `embedder.model_name = "all-MiniLM-L6-v2"`
- Keep `DummyEmbedder` for tests (it's perfect for that)
- Update `MemoryIndex` dim to match the model's output (384 for MiniLM)
- **Incremental indexing**: add a method to `MemoryIndex` that can add new documents without rebuilding the whole index

---

## Phase 2: Safety & Control

> Wire up the trust boundary so the system is safe to actually use.

### 2.1 Canonical Event Schema

**Why before everything else in this phase**: Schema drift between Rust/Python/HUD is the biggest long-term maintainability risk. Define typed payloads now, before the event vocabulary expands further (see AP-3).

**Rust side:**

```rust
#[derive(Serialize, Deserialize, Debug, Clone)]
#[serde(tag = "type")]
pub enum EventPayload {
    UserInput { text: String, context: Value },
    ToolRequest { task_id: String, tool_name: String, args: Value, danger_tier: String },
    ToolResult { task_id: String, tool_name: String, result: Value },
    ToolRejected { task_id: String, tool_name: String, reason: String },
    ToolConfirmationRequired { task_id: String, tool_name: String, args: Value, danger_tier: String },
    ToolConfirmed { task_id: String, tool_name: String },
    ToolDenied { task_id: String, tool_name: String },
    MemoryRetrieved { query: String, results: Vec<Value> },
    IntentContracted { contract: IntentContractPayload },
    ContextUpdated { data: Value },
    SystemSuspend { reason: String },
    SystemResume {},
}
```

**Python side:**

```python
from pydantic import BaseModel

class UserInputPayload(BaseModel):
    text: str
    context: dict

class ToolRequestPayload(BaseModel):
    task_id: str
    tool_name: str
    args: dict
    danger_tier: str

class ToolResultPayload(BaseModel):
    task_id: str
    tool_name: str
    result: dict

# ... all variants mirrored
```

**Enforcement rule**: If a payload doesn't match its schema, it is rejected at runtime. No "best effort parsing." Both Rust and Python validate on receive.

### 2.2 Intent Contract Layer

**Why before the capability system**: The Intent Contract stabilizes the user's intent before execution begins. Without it, retries drift, replanning loses the original goal, and interruption has no resumption point (see AP-1).

- After classification, the orchestrator produces an `IntentContract` object:
  - `objective`: what the user wants (parsed from input + context)
  - `constraints`: what must not happen (derived from safety rules + user history)
  - `requires_tools`: whether tool use is expected
  - `requires_confirmation`: whether user approval is needed (based on tool danger tiers)
  - `persistence_policy`: should this interaction be memorized? (`always`, `if_useful`, `never`)
  - `expected_output_type`: text, file, status, etc.
- The Intent Contract is emitted as an event (`intent.contracted`) and stored in task state
- All downstream execution (planning, tool calls, retries, replanning) must reference the contract
- On retry: the retry must still satisfy the original contract's objective and constraints
- On replan: the new plan must satisfy the same contract
- On interruption: the contract is the resumption anchor

**Rust side:**

```rust
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct IntentContract {
    pub objective: String,
    pub constraints: Vec<String>,
    pub requires_tools: bool,
    pub requires_confirmation: bool,
    pub persistence_policy: String,
    pub expected_output_type: String,
}
```

**Python side:**

```python
class IntentContract(BaseModel):
    objective: str
    constraints: list[str]
    requires_tools: bool
    requires_confirmation: bool
    persistence_policy: str  # "always" | "if_useful" | "never"
    expected_output_type: str  # "text" | "file" | "status" | "none"
```

### 2.3 Capability-First Authorization

**Mental model shift**: confirmation is one way to obtain a capability, not the capability system itself (see AP-2).

- `CapabilityToken` becomes the authorization primitive, not an afterthought
- On `tool.requested`: core checks if a valid capability already exists for the tool + task + scope
- **Capability sources** (in priority order):
  1. **Existing valid token** — already authorized, execute immediately
  2. **Session-scoped permission** — "allow `run_shell` with `ls` commands for 10 minutes" (config or previously granted)
  3. **Confirmation dialog** — ask the user via HUD
  4. **Denied** — no capability available, reject
- Tokens are stored in `SystemState` with scope, TTL, and constraints
- **Scope types**: `single_use`, `session_scoped`, `time_limited`, `project_scoped`
- **Confirmation flow** becomes one UI for capability acquisition, not the authorization system itself

**Event flow**:

```
orchestrator → tool.requested
    → core checks capability store
    → if valid token exists: execute immediately
    → if session permission exists: execute immediately
    → if neither: emit tool.confirmation_required → HUD
    → user approves: issue CapabilityToken, execute
    → user denies: emit tool.rejected
```

**Future-enabling**: this architecture supports trusted workflows, automation macros, and proactive behavior — all without changing the authorization model.

### 2.4 Tool Sandboxing (Basic)

- `run_shell` currently runs with full user permissions
- Add configurable command blacklist in config: `[security] blocked_commands = ["rm -rf /", "mkfs", "dd if=/dev/zero"]`
- Add path restrictions: `[security] allowed_paths = ["/home/jperez", "/tmp"]`
- Core validates shell commands against these rules before execution
- This is **not** a full sandbox (that would need namespaces/seccomp), but it's a practical first layer
- Validation happens at the capability acquisition stage, not after

---

## Phase 3: Completeness

> Fill in the spec gaps that make Astra a complete system.

### 3.1 Full State Machine

The spec defines 10 states; the reducer handles 4 events. Fill this in:

- Add all spec event types to the reducer: `task.updated`, `task.completed`, `task.failed`, `memory.retrieved`, `memory.write`, `tool.rejected`, `tool.confirmation_required`, `intent.contracted`, `task.interrupted`
- Add all spec states: `capturing`, `classifying`, `retrieving`, `planning`, `executing`, `waiting_confirmation`, `recovering`, `completed`, `cancelled`, `interrupted`, `timed_out`
- State transitions follow the spec's pipeline, now with the Intent Contract as the stabilization layer between classification and planning
- **Tests**: state machine transition tests for every valid path

**State transition table**:

```
idle          → capturing        (on ui.input)
capturing     → classifying      (on input captured)
classifying   → intent_contracted (on intent classified)
intent_contracted → retrieving   (on contract produced)
retrieving    → planning         (on memory retrieved)
planning      → executing        (on plan ready, contract-validated)
executing     → waiting_confirmation  (on tool.confirmation_required)
executing     → completed        (on tool.completed, no more steps)
executing     → interrupted      (on task.interrupted, see AP-7)
waiting_confirmation → executing (on tool.confirmed → capability granted)
waiting_confirmation → recovering (on tool.denied → no capability)
recovering    → planning         (on replan, must satisfy original contract)
recovering    → cancelled        (on max retries exceeded)
interrupted   → recovering       (on context_invalidated, if constraints violated)
interrupted   → executing        (on context_invalidated, if ignorable)
interrupted   → cancelled        (on user_cancelled)
interrupted   → executing        (on system_resume, after system_suspend)
completed     → idle             (on result delivered)
cancelled     → idle             (on cleanup done)
timed_out     → recovering       (on retryable)
timed_out     → cancelled        (on not retryable)
```

Key differences from the original roadmap:
- `classifying` now produces an `IntentContract` before `retrieving`/`planning` — replanning and retries always have a stable reference
- `interrupted` is a first-class state with explicit reasons (see AP-7) — not just "cancelled"
- `timed_out` is distinct from `cancelled` — it may be retryable
- Context invalidation can either resume execution (ignorable) or trigger recovery (constraints violated)

### 3.2 Model Routing (Single-Model Strategy)

Since we're running one model, routing becomes **prompt strategy routing** rather than model switching:

- `route_task()` returns the same `LlamaClient` but with different parameters per task type:
  - `classification`: low temperature (0.1), short max_tokens (128)
  - `reasoning`: medium temperature (0.7), medium max_tokens (512)
  - `deep`: higher temperature (0.8), long max_tokens (1024)
- The Intent Contract's `requires_tools` and `expected_output_type` fields feed directly into routing decisions
- Add a lightweight **intent classifier** in the orchestrator: before the full agent cycle, do a fast LLM call (or heuristic) to classify the input as `chat`, `tool_request`, `memory_operation`, or `multi_step`
- Route prompt template and parameters based on classification
- **Future-ready**: the routing interface stays the same, so swapping in a second model server later is a config change, not a code change

### 3.3 Error Recovery & Interruption System

**Error recovery:**

- **Retry logic**: on `tool.failed`, check `retryability`. If retryable and retries < max (configurable), auto-retry with backoff. **Critical**: retry must satisfy the original Intent Contract — if the objective or constraints have changed, do not retry the same plan.
- **Fallback tools**: define fallback tools in the registry (e.g., if `find` fails, try `ls -R`)
- **Replan trigger**: if a tool fails 3 times, emit `task.replan_requested` → orchestrator re-plans with the LLM, but the new plan must still satisfy the original Intent Contract
- **Error classification**: `transient` (retry), `deterministic` (replan), `permission` (escalate to user), `critical` (abort)
- Add `retries` and `max_retries` to `Task` state (partially there already)

**Interruption semantics** (see AP-7):

Formal interruption handling is essential before multi-step plans and background tasks. Every interruption must carry a reason, and the system must decide whether execution can resume.

- Add `InterruptReason` to the event schema and task state
- On `task.interrupted`: core records the reason, preserves partial progress, and transitions to the `interrupted` state
- **Interruption handling rules**:
  - `user_cancelled` → immediate halt, preserve partial progress, mark task cancelled
  - `capability_revoked` → immediate halt, preserve partial progress, mark task awaiting re-authorization
  - `dependency_failed` → halt downstream, preserve completed steps, offer replan
  - `context_invalidated` → evaluate severity against Intent Contract; if constraints violated, halt and offer replan; if ignorable, continue with warning
  - `timeout` → halt, preserve partial progress, mark task timed_out
  - `system_suspend` → pause execution, preserve full state, resume on `system.resume`
- **Context invalidation detection** (Phase 5 prerequisite): the core must be able to detect when the execution environment has changed under an active task. This is a lightweight check at each step boundary, not continuous polling.
- **Tests**: interruption at every state, resumption after each interrupt reason, context invalidation with both ignorable and constraint-violating changes

### 3.4 Structured Tool Channels (Delimited Output)

**This is the second stage of AP-4**: after robust extraction (Phase 1.3), move to explicit delimiters separating conversational text from tool calls.

- Update the prompt to instruct the LLM to use explicit markers:

```
assistant text here
TOOL_CALL_START
{"tool_name": "run_shell", "args": {"cmd": "ls -la ~"}}
TOOL_CALL_END
```

- Parser looks for `TOOL_CALL_START` / `TOOL_CALL_END` delimiters first, falls back to JSON extraction
- This eliminates the "which JSON block is the tool call?" ambiguity
- Everything between delimiters is parsed as structured tool intent; everything outside is conversational text
- **Tests**: mixed text+tool output, multiple tool calls, tool calls with no surrounding text, malformed delimiters

### 3.5 Evaluation & Replay Infrastructure

**Why before advanced autonomy**: Astra is approaching the complexity level where evaluation becomes a feature. Without it, you're flying blind on quality regressions.

- **Golden conversation traces**: save canonical input→output pairs as reference files in `tests/traces/`
- **Deterministic replay**: given a session ID, replay all events from SQLite to reconstruct state. **With `ExecutionContext`** (Phase 1.4), replay is actual deterministic reproduction — you know exactly which model, prompt, memory set, and tool registry produced each decision. Without it, replay is approximate historical reconstruction.
- **Planner regression suites**: run golden traces against the current planner, flag deviations. When a deviation is detected, `ExecutionContext` allows pinpointing whether the regression came from the model, the prompt template, the memory retrieval set, the tool registry, or the planner logic itself.
- **Tool-call correctness benchmarks**: measure tool call success rate, argument validity rate, hallucination rate
- **Memory retrieval relevance scoring**: for a set of queries, measure whether the top-k retrieved chunks are actually relevant (manual annotation at first, automated later)
- **Replay CLI**: `astra replay <session_id>` — reconstructs and displays the full event sequence for a session, including the `ExecutionContext` at each decision point
- **Regression isolation**: when a golden trace fails, the system can diff the `ExecutionContext` between the passing and failing run to identify the root cause

### 3.6 Conversation History in HUD

- HUD currently shows only the **last** response — no scrollback
- Add a message list component: each `ui.output` event appends to a scrollable list
- Different styling for: user messages, assistant text, tool execution tags, tool results, confirmation dialogs
- Conversation is already persisted in SQLite (Phase 1.4) — HUD reads from it on reconnect
- This is now primarily a HUD frontend change, not a backend change

---

## Phase 4: Memory System Maturity

> Make memory a true first-class system, not just a stub.

### 4.1 Obsidian Vault Integration

- `save_memory` currently appends to a flat `vault_memories.md` — this doesn't scale
- Restructure: memories are saved as individual markdown files in the vault, organized by type:
  - `memories/preferences/` — user preferences
  - `memories/procedures/` — how-to knowledge
  - `memories/facts/` — stable facts
  - `memories/logs/` — task history summaries
- Each file gets YAML frontmatter: `id`, `timestamp`, `tags`, `source`, `confidence`
- `parser.py` reads frontmatter as metadata (not just paragraph chunks)

**Example memory file**:

```markdown
---
id: mem_20260511_001
timestamp: 2026-05-11T15:30:00
tags: [preference, editor]
source: auto
confidence: 0.9
---

User prefers Neovim over VS Code for editing configuration files.
They use the LazyVim distribution.
```

### 4.2 Memory Write Policy

- Not everything should be saved — implement the spec's write policy:
  - **Store**: stable facts, workflows, preferences
  - **Ignore**: transient chatter, duplicates
  - **Prefer**: summaries over raw logs
- The Intent Contract's `persistence_policy` field drives this decision:
  - `always` → save regardless
  - `if_useful` → apply the `should_store()` heuristic
  - `never` → skip storage
- Add a `should_store()` heuristic in the orchestrator: after each agent cycle, evaluate if the interaction produced store-worthy knowledge
- Deduplication: before saving, check if similar content already exists (embedding similarity > 0.95)

### 4.3 Memory Conflict Resolution

- When new memory contradicts existing memory:
  - Prefer newer info if time-sensitive
  - Prefer explicit user statements
  - Mark old entries as `superseded_by: <new_id>` in frontmatter
- Add a `memory.conflict` event type

### 4.4 Incremental Index Rebuild

- On startup: check vault file modification times vs. last index build
- Only re-embed and re-index changed files
- Store index metadata (last-built timestamp, file hashes) in SQLite
- Full rebuild only on first run or config change

---

## Phase 5: Context Awareness

> Make Astra aware of what you're doing, not just what you're typing.
> This phase makes context invalidation (AP-7) a real, frequent event — not a theoretical concern.

### 5.1 Active Window Tracking

- Core polls `hyprctl activewindow` periodically (or subscribes to Hyprland events via socket)
- Emits `context.window_changed` events with: app name, title, workspace
- Orchestrator injects active window info into `active_context`
- **Interruption implication**: if the active window changes during a multi-step task, the core evaluates whether this constitutes a context invalidation (see AP-7). A switch from a terminal in project A to a browser is likely ignorable; a switch from project A's terminal to project B's terminal may invalidate the task's assumptions.

### 5.2 Clipboard Integration

- On HUD open: read current clipboard content
- Include in `ui.input` event as `context.clipboard`
- Orchestrator can use clipboard content as additional context
- **Interruption implication**: clipboard changes during task execution are usually ignorable, but if the task was explicitly using clipboard content (e.g., "rename the file whose path is in my clipboard"), a clipboard change is a context invalidation.

### 5.3 Project-Aware Context

- If the active window is a terminal/editor in a git repo, detect the project root
- Include project path, recent git log, and file listing in context
- This makes "help me with this project" actually work
- **Interruption implication**: git branch changes and external file modifications are the most impactful context invalidations. If a task is operating on files in a repo and the user switches branches, the task's assumptions about file contents may be invalidated. The core must detect this and evaluate against the Intent Contract's constraints.

---

## Phase 6: Advanced Execution

> The ambitious spec features — only tackle these after the foundation is solid.
> Follow the progression: single-step robustness → linear plans → branching DAGs (see AP-5).

### 6.1 Linear Multi-Step Plans

**Do not skip to DAGs.** Start with ordered sequences:

- LLM can propose a sequence of tool calls (a linear plan)
- Core stores the plan as an ordered list in task state
- Executes steps sequentially, feeding results forward
- User can review the plan before execution starts
- Each step must satisfy the Intent Contract
- If any step fails: stop, report partial progress, offer replan from failure point
- **Cancellation**: user can cancel at any step; completed steps remain valid
- **Interruption**: any `InterruptReason` (see AP-7) can halt the plan mid-execution. Partial progress is preserved. On resumption, the plan continues from the last completed step (unless context invalidation requires replanning).
- **Execution Context**: each step in the plan captures its own `ExecutionContext`, so if a step produces different results after a model or prompt change, the regression is traceable.

### 6.2 Branching DAG Execution

**Only after linear plans are robust.**

- Extend linear plans to support conditional branches and parallel steps
- Core stores the plan as a DAG in task state
- DAG scheduler runs continuously in the event loop
- Tools execute only when dependencies are complete
- Partial failures propagate downstream; downstream nodes are invalidated
- Cycle detection on DAG construction
- **State snapshots**: before each DAG execution, snapshot state so partial rollback is possible

### 6.3 Background Tasks

- Long-running tools execute asynchronously
- HUD shows a task status panel (running, completed, failed)
- Tasks survive orchestrator restarts (state in SQLite)
- Background tasks are bounded by Intent Contracts — they can be cancelled if the contract is violated
- **Interruption is the hardest problem for background tasks**: a background task runs without user attention, so context invalidation (file changed, branch switched, project changed) may go unnoticed. The core must actively monitor the execution environment and emit `task.interrupted` with `context_invalidated` when the environment drifts from the task's assumptions. This is where the formal interruption model (AP-7) becomes critical — without it, background tasks silently operate on stale assumptions.

### 6.4 Streaming LLM Output

- Instead of waiting for the full response, stream tokens to the HUD
- Requires switching from `/v1/completions` to a streaming endpoint
- HUD renders text incrementally (typewriter effect)
- Streaming must respect the structured tool channel delimiters — tool calls are not streamed character-by-character; they appear atomically once complete

### 6.5 Constrained Decoding

**The final stage of AP-4**: grammar-constrained decoding that makes invalid tool calls syntactically impossible.

- Configure the LLM server with a grammar that enforces the tool-call schema
- The model can only output valid tool calls or conversational text — never malformed hybrids
- This eliminates the entire class of parsing failures
- Requires LLM server support (llama.cpp supports grammar-constrained decoding)

---

## Dependency Graph

```
Phase 1 (Foundation) ──→ Phase 2 (Safety) ──→ Phase 3 (Completeness)
                                                      │
                                          ┌───────────┼───────────┐
                                          ▼           ▼           ▼
                                   Phase 4       Phase 5      Phase 6
                                   (Memory)      (Context)    (Advanced)
```

Phases 1 → 2 → 3 are sequential (each builds on the previous).
Phases 4, 5, and 6 can be parallelized after Phase 3, though Phase 4 is recommended before Phase 5 (context awareness is more useful with good memory).

**Within Phase 1, the order matters**:

```
1.1 Config → 1.2 Logging → 1.3 Tool Parsing → 1.4 Conversation Persistence → 1.5 Embeddings
```

Config unblocks everything. Logging must be in place before you change parsing and memory (observability first). Conversation persistence is foundational infrastructure, not UX polish. Embeddings come last because debugging them requires all the above.

---

## Risks & Tradeoffs

| Risk | Mitigation |
|------|-----------|
| Sentence-transformers adds a heavy dependency | Keep DummyEmbedder as fallback; RealEmbedder is optional via config |
| Capability system adds complexity to every tool call | Start with single-use tokens only; add session-scoped and time-limited later |
| Intent Contract adds a step to the pipeline | The contract is lightweight — it's produced by the classifier that already exists conceptually |
| Canonical event schema requires coordinated Rust+Python changes | Define the schema in a shared spec file; both sides generate from it |
| Full state machine is complex to implement correctly | Implement incrementally — add states as features need them, not all at once |
| Single-model routing is limited | Interface is designed for multi-model; swapping in a second server is a config change |
| TOML config in both Rust and Python could drift | Share a validation schema; both read the same file |
| HUD confirmation dialog needs Tauri event work | Start with a simple modal; refine UX later |
| Multi-step planning is where assistant projects collapse | Follow the progression: single-step → linear → DAG. Never skip to arbitrary DAGs. |
| Structured tool channels require prompt changes | Delimiters are backward-compatible — parser falls back to JSON extraction if no delimiters found |
| Evaluation infrastructure has no immediate user-facing value | It pays off starting in Phase 4 — every memory and context change becomes verifiable |
| ExecutionContext adds storage overhead | Contexts are small (a few hundred bytes per task). The value for regression analysis far outweighs the cost. |
| Context invalidation detection is expensive or noisy | Start with conservative detection (only check at step boundaries, only for file/branch changes). Tune thresholds based on real usage. |
| Interruption semantics make the state machine more complex | The alternative is worse: silent corruption when tasks operate on stale context. Explicit states are always better than implicit bugs. |
| Background tasks with context monitoring create a surveillance surface | Monitoring is limited to the task's own dependencies (files it touched, branch it was on), not general filesystem surveillance. |

---

## Recommended Starting Point

**Phase 1.1 (Config System) + Phase 1.2 (Structured Logging)** — these are the highest-leverage changes. Config unblocks everything else, and logging must be in place before you touch parsing or memory. They can be done in parallel since they don't touch the same files.

After that: **Phase 1.3 (Tool Parsing)** eliminates the most common failure mode, and **Phase 1.4 (Conversation Persistence)** provides the observability foundation that every subsequent phase depends on.
