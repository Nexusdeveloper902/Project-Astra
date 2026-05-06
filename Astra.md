# Project Astra – System Design Document

## 1. Overview
Project Astra is a local, tool-augmented AI assistant designed to function as a lightweight personal operating layer over a Linux system. It is built to provide fast, context-aware interactions, automate tasks, manage knowledge, and act as a unified interface between the user and their environment. 

Astra is not just a chatbot. It is a modular cognitive system combining memory, reasoning, tool execution, context awareness, and state management into a single unified assistant layer.

---

## 2. Core Design Philosophy

### 2.1 Minimal Friction Interaction
* Single global hotkey invocation
* Ephemeral overlay UI (no full app switching)
* Automatic intent inference (no manual mode selection)

### 2.2 Tool-First Intelligence
* All capabilities are exposed as tools
* The model decides when to act vs respond
* Execution is first-class, not optional

### 2.3 Local-First Architecture
* Runs primarily on local hardware (Linux-first)
* Offline-capable core system
* External APIs are optional modules

### 2.4 Memory as a First-Class System
* Long-term memory stored in Obsidian (Astra Vault)
* Retrieval-Augmented Generation (RAG)
* Automatic capture of relevant knowledge

---

## 3. High-Level Architecture
Astra consists of layered subsystems:

### 3.1 Interaction Layer
* Global hotkey trigger
* Ephemeral overlay (Astra HUD)
* Text + optional voice input
* Context injection (clipboard, selection, active app)

### 3.2 Intent Processing Layer
* Classifies input into:
    * conversational response
    * tool execution
    * memory operation
    * multi-step task planning
* Produces structured intent objects

### 3.3 Core Reasoning Engine
* Local LLM (model routing system)
* Handles planning, decomposition, reasoning
* Selects appropriate tools and memory

### 3.4 Tool Execution Layer (Astra Runtime)
* Executes system actions
* Runs scripts and subprocesses
* Interfaces with Linux system (Hyprland-aware)
* Enforces permissions and sandboxing

### 3.5 Memory System (Astra Vault)
* Obsidian-based structured knowledge base
* Vector index for semantic retrieval
* Automatic ingestion pipeline

### 3.6 Context Awareness Layer
* Active window tracking
* Clipboard monitoring
* Selection capture
* Project-aware context injection

---

## 4. Core Execution Pipeline
Astra operates through a structured loop:

**Capture → Classify → Retrieve → Plan → Decide → Act → Validate → Store → Feedback**

### Steps:
1. Capture input + system context
2. Classify intent
3. Retrieve relevant memory/context
4. Plan actions or response
5. Decide execution path
6. Execute tools or generate output
7. Validate outputs
8. Store relevant memory
9. Feed results into feedback system

---

## 5. Tool System
Astra uses a strict, typed tool system rather than free-form execution.

### 5.1 Tool Definition Schema
Each tool includes:
* name
* description
* input_schema
* output_schema
* permission_level
* side_effects
* timeout_ms
* danger_tier (low / medium / high / critical)

---

### 5.2 Invocation Contract
Tool calls are structured:
* tool name
* arguments (JSON)
* request ID
* session context
* confirmation flag (if required)

---

### 5.3 Permission System
* **Low-risk tools**: automatic execution
* **Medium-risk tools**: contextual validation
* **High-risk tools**: explicit user confirmation
* **Critical tools**: always blocked until explicit approval

Permissions are enforced **before execution**, not after.

---

### 5.4 Output Validation
* Schema validation of outputs
* Size limits and truncation rules
* Structured error normalization
* Safety filtering of sensitive outputs

---

### 5.5 Failure Propagation
Failures become structured objects:
* error type
* message
* retryability
* suggested fix
* stack/trace (if safe)

These feed directly into:
* retry logic
* fallback tools
* user escalation
* debugging mode

---

## 6. Memory System – Astra Vault

### 6.1 Storage Structure
* Obsidian markdown vault
* Organized into:
    * Projects
    * Concepts
    * Logs
    * System notes

---

### 6.2 Memory Granularity
* **Primary**: note-level storage
* **Secondary**: chunk/paragraph-level indexing
* Chunks retain context + metadata

---

### 6.3 Embeddings & Indexing
* Embeddings generated per chunk
* Vector index stored separately
* Supports fast similarity search
* Incremental updates supported
* Metadata store tracks:
    * timestamps
    * tags
    * source file
    * confidence score

---

### 6.4 Memory Types
* Explicit user notes
* Auto-captured insights
* Task history
* Preferences
* Procedural knowledge

---

### 6.5 Write Policy
Astra only stores useful information:
* **Store**: stable facts, workflows, preferences
* **Ignore**: transient chatter, noise, duplicates
* **Prefer**: summaries over raw logs
* **Attach provenance** to all entries

---

### 6.6 Conflict Resolution
When contradictions occur:
* Prefer newer info (if time-sensitive)
* Prefer explicit user statements
* Preserve conflicting entries when uncertain
* Mark outdated entries as “superseded”

---

### 6.7 Retrieval Policy
* Semantic search first
* Keyword fallback second
* Context-scoped retrieval preferred
* Ranked by relevance, recency, confidence

---

## 7. Model Routing System

### 7.1 Inputs to Routing
* task type
* input length
* context size
* latency budget
* tool likelihood
* reasoning complexity
* classification confidence

---

### 7.2 Model Tiers
* **Small model**: classification, extraction, quick replies
* **Medium model**: general reasoning, tool planning
* **Large model**: deep reasoning, architecture, complex coding

---

### 7.3 Routing Logic
* Heuristic rules for obvious cases
* Lightweight classifier for ambiguity
* Confidence threshold escalation

---

### 7.4 Fallback Policy
* Escalate if uncertain
* Retry on failure
* Never block user response entirely

---

### 7.5 Cost Strategy
* Prefer smallest sufficient model
* Reserve large models for complex tasks
* Optimize for responsiveness

---

## 8. User Interface – Astra HUD
* Minimal overlay interface
* Keyboard-first interaction
* Optional voice input
* Shows:
    * input box
    * active context
    * tool execution status
    * memory suggestions

---

## 9. Automation Layer

### 9.1 Autonomy Levels
* **L0**: suggestions only
* **L1**: requires confirmation
* **L2**: limited autonomous execution
* **L3**: supervised multi-step automation

---

### 9.2 Task Tracking System
Each task contains:
* task ID
* goal
* current step
* status
* retries
* pending actions
* cancellation flag

---

### 9.3 Cancellation Model
* User can interrupt at any time
* Immediate halt of future actions
* Partial progress preserved when possible

---

### 9.4 Background Tasks
* Visible task registry
* Resumable execution
* Scoped to goals
* Bound by safety rules

---

## 10. Context Awareness

### 10.1 Signals
* active window
* clipboard
* selection
* project directory
* optional screenshots (opt-in)

---

### 10.2 Sampling Strategy
* Event-driven capture (not constant polling)
* Deduplication of repeated signals
* Rate limiting for noisy sources

---

### 10.3 Relevance Filtering
* Only meaningful context is retained
* Transient data treated as ephemeral
* Summaries preferred over raw capture

---

### 10.4 Privacy Model
* Fully local by default
* Sensitive data not persisted unless required
* Explicit boundaries for capture/storage

---

## 11. Security Model

### 11.1 Sandboxing
* Restricted shell execution
* Isolated subprocesses
* Controlled file access

---

### 11.2 Confirmation Rules
Always require confirmation for:
* destructive operations
* system changes
* network-sensitive actions
* privilege escalation
* high-risk automation

---

### 11.3 Danger Tiers
* **Low**: safe, reversible
* **Medium**: limited impact
* **High**: system-altering
* **Critical**: potentially destructive

---

### 11.4 Escalation Policy
* No automatic privilege escalation
* Requires explicit user approval

---

## 12. Extensibility
* Modular tool system
* Pluggable memory systems
* Swappable model backends
* UI replaceable layers
* Versioned policy engine

---

## 13. System State Model
Astra maintains explicit runtime state:

### 13.1 State Objects
* task stack
* active goal
* pending tools
* memory set
* context window
* confirmation queue
* interruption state

---

### 13.2 State Machine
States:
* idle
* capturing
* classifying
* retrieving
* planning
* executing
* waiting_confirmation
* recovering
* completed
* cancelled

---

### 13.3 Interruption Handling
* Any user input interrupts execution
* State is preserved where possible
* Tasks can resume after interruption

---

## 14. Future Expansions
* Voice-first mode
* Multi-agent Astra subsystems
* Predictive automation
* Distributed execution across devices
* Self-optimizing workflows
* Persistent autonomous background agents

---

## 15. Summary
Project Astra is a local-first intelligent assistant system built around:
* Tool-based execution
* Persistent semantic memory
* Context-aware reasoning
* Dynamic model routing
* Explicit state management
* Strict safety boundaries

It functions as a cognitive layer over the operating system, turning intent into structured action while maintaining full user control and system transparency.

---

## 16. Tool Execution Protocol (Runtime-Level Spec)
This defines the exact flow of a tool call from LLM → runtime → result → model.

### 16.1 Tool Call Format (LLM → Runtime)
All tool calls are emitted as structured JSON messages:

```json
{
  "type": "tool_call",
  "id": "call_001",
  "tool": "run_shell",
  "args": {
    "cmd": "ls -la"
  },
  "context": {
    "task_id": "task_123",
    "model": "medium",
    "user_intent": "inspect directory"
  },
  "execution": {
    "mode": "sync",
    "timeout_ms": 5000,
    "stream": false
  }
}
```

### 16.2 Execution Modes

#### Sync Execution
LLM waits for tool result before continuing.
Used for:
* file reads
* queries
* short shell commands

#### Async Execution
Tool runs in background. Returns task handle immediately.

```json
{
  "type": "tool_ack",
  "call_id": "call_002",
  "status": "running",
  "task_handle": "task_999"
}
```

### 16.3 Streaming Tools
Tools may stream incremental output:

```json
{
  "type": "tool_stream",
  "call_id": "call_003",
  "chunk": "processing line 1..."
}
```

Final response:
```json
{
  "type": "tool_result",
  "call_id": "call_003",
  "output": "complete result",
  "status": "success"
}
```

### 16.4 Tool Result Return Flow
1. Tool executes in runtime
2. Runtime validates output
3. Output is wrapped:

```json
{
  "type": "tool_result",
  "call_id": "call_001",
  "tool": "run_shell",
  "status": "success",
  "output": "...",
  "meta": {
    "duration_ms": 120,
    "stdout_size": 1024
  }
}
```

4. Returned to LLM as context message

### 16.5 Failure Format

```json
{
  "type": "tool_error",
  "call_id": "call_004",
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "write access blocked",
    "retryable": false
  }
}
```

---

## 17. Event Bus Architecture (Core Missing Layer)
Astra is event-driven, not pipeline-only.

### 17.1 Core Principle
Every subsystem communicates via events:
* memory
* tools
* context
* UI
* reasoning engine
* task manager

### 17.2 Event Format

```json
{
  "event": "context.updated",
  "timestamp": 1710000000,
  "source": "context_layer",
  "data": {}
}
```

### 17.3 Event Types

#### Input Events
* `user.input`
* `ui.command`
* `hotkey.trigger`

#### System Events
* `context.updated`
* `memory.retrieved`
* `tool.requested`
* `tool.completed`
* `tool.failed`

#### Task Events
* `task.created`
* `task.updated`
* `task.completed`
* `task.failed`
* `task.cancelled`

### 17.4 Communication Model
* Fully asynchronous event bus
* Components subscribe to event types
* No direct coupling between subsystems

**Example**: UI → emits `user.input` → Intent Engine listens → emits `task.created` → Tool Runtime listens → emits `tool.completed` → Memory listens → UI listens

---

## 18. Persistent Storage Architecture

### 18.1 Storage Layers

1. **Obsidian Vault**
   * Human-readable memory
   * Long-term structured knowledge

2. **SQLite System DB**
   * Used for: task state, tool logs, event history, session state

3. **Vector Database**
   * Options: FAISS (local fast index) or SQLite-embedded vector extension
   * Stores: embeddings, chunk references, similarity metadata

### 18.2 Memory Entry Schema

```json
{
  "id": "mem_001",
  "text": "...",
  "embedding_id": "vec_123",
  "source": "auto|manual",
  "timestamp": 1710000000,
  "tags": ["project", "astra"],
  "confidence": 0.82
}
```

### 18.3 Incremental Indexing
* New note → chunk → embed → append index
* No full rebuild required
* Background batch indexing allowed

### 18.4 Backup Strategy
* Obsidian = git-backed
* SQLite = periodic snapshot dumps
* Vector DB = regenerable from notes

---

## 19. Latency & Performance Model

### 19.1 Model Budgets
| Tier | Max Latency | Use Case |
|------|-------------|----------|
| Small | 300ms–1s | classification |
| Medium | 1–5s | reasoning |
| Large | 5–20s | deep tasks |

### 19.2 Tool Execution Limits
* default timeout: 5s
* long tasks: async only
* hard cap: 60s per tool unless elevated

### 19.3 Memory Retrieval Budget
* max 20 chunks per query
* max 1–3MB context injection
* reranking required if overflow

### 19.4 Context Window Management
* sliding window strategy
* compression of old dialogue
* summarization layer when threshold exceeded

---

## 20. Prompt Orchestration Layer (Critical Missing Piece)
This defines how the final prompt is constructed.

### 20.1 Prompt Structure
`SYSTEM CORE INSTRUCTION + USER INPUT + ACTIVE CONTEXT + MEMORY RETRIEVALS + TOOL SCHEMA DEFINITIONS + TASK STATE + RECENT TOOL RESULTS`

### 20.2 Memory Injection Format
```text
[Memory]
- User prefers Arch Linux
- Project Astra uses Hyprland
- Prior decision: Obsidian vault is primary memory
```

### 20.3 Tool Schema Injection
Only active tools are included:
```text
Available tools:
- run_shell(cmd)
- read_file(path)
- write_file(path, content)
```

### 20.4 Context Compression
When token limit approaches:
* summarize conversation
* retain only: open tasks, unresolved tool results, active goals

### 20.5 Token Budget Allocation
* 40% reasoning
* 30% memory
* 20% tools
* 10% system instructions (dynamic adjustment based on task type)

---

## 21. UI Contract (Astra HUD Runtime Behavior)

### 21.1 UI → System Events
UI emits:
```json
{
  "event": "ui.input",
  "text": "...",
  "context": {
    "active_app": "terminal"
  }
}
```

### 21.2 Interrupt Handling
```json
{
  "event": "ui.cancel",
  "task_id": "task_123"
}
```
Immediately:
* stops tool execution
* flags task as cancelled
* emits `task.cancelled`

### 21.3 Streaming Updates to UI
* tool progress
* partial LLM output
* memory retrieval results

**Example**:
```json
{
  "event": "ui.update",
  "type": "tool_progress",
  "message": "Downloading dependencies..."
}
```

---

## 22. Observability & Logging System

### 22.1 Log Types
* system logs
* tool logs
* memory logs
* model logs
* event logs

### 22.2 Tool Execution Trace
```json
{
  "trace_id": "t_001",
  "tool": "run_shell",
  "input": "...",
  "output": "...",
  "latency_ms": 120,
  "status": "success"
}
```

### 22.3 Replay System (Critical for debugging)
Astra can replay any session:
* restore event sequence
* re-run tool calls
* simulate reasoning path

This is essential for debugging agent behavior.

### 22.4 Metrics
* tool success rate
* average latency per model tier
* memory retrieval hit rate
* task completion rate
* failure clustering

---

## 23. Recovery & Repair System

### 23.1 Recovery Triggers
* tool failure
* invalid output
* timeout
* model uncertainty
* state inconsistency

### 23.2 Recovery Actions
Astra can:
1. **Retry**: same tool, adjusted parameters
2. **Fallback**: switch to alternative tool
3. **Replan**: regenerate task plan
4. **Escalate**: ask user for clarification

### 23.3 Partial Rollback
If step N fails:
* steps 1..N-1 remain valid
* state is rewound to last stable checkpoint
* downstream tasks are invalidated

### 23.4 Branching Recovery
Astra can create alternative execution branches:
Plan A fails → generate Plan B. Both are tracked in task history.

### 23.5 Recovery State Machine
* `recover_attempting`
* `recover_replanning`
* `recover_fallback`
* `recover_user_query`
* `recover_failed` (final state)

---

## FINAL SUMMARY
With these additions, Project Astra is now fully defined as a complete agent architecture consisting of:
* deterministic tool execution protocol
* event-driven system bus
* persistent multi-layer storage
* explicit latency and performance model
* structured prompt orchestration layer
* UI ↔ system real-time contract
* full observability + replay system
* recovery + repair engine
* stateful task machine

---

## 24. Concurrency Model (Deterministic Execution Core)

### 24.1 Core Principle
Astra uses a hybrid single-event-loop + worker pool model:
* **Single-threaded event bus** (authoritative state)
* **Multi-threaded / async workers** (tool execution only)

This avoids race conditions in state while still allowing parallel execution.

### 24.2 System Structure
* **Event Loop** (Single Owner of State): Processes all events sequentially, applies state transitions deterministically, emits new events.
* **Worker Pool**: Executes tools (shell, IO, network, ML inference). Stateless execution environment. Cannot mutate system state directly.

### 24.3 Rule
Only the event loop may mutate state. Workers execute and return results, but never modify shared state.

### 24.4 Race Condition Prevention
Events are timestamp-ordered but processed sequentially. If two events conflict, the event loop resolves using deterministic priority rules:
`user input > system events`
`cancellation > execution`
`latest task version wins`

### 24.5 Task Locking
Each task has:
```json
{
  "task_id": "t1",
  "lock": "exclusive | shared | none"
}
```
* **exclusive**: only one execution path
* **shared**: multiple reads allowed
* **none**: stateless operations

---

## 25. Canonical State Store Model

### 25.1 State Ownership
There is ONE authority: The Event-Sourced State Reducer.

### 25.2 Architecture
`Events → Reducer → State Snapshot → Runtime View`
State is NOT mutated directly.

### 25.3 Event-Sourced State
Every change is an event:
```json
{
  "event": "task.updated",
  "task_id": "t1",
  "change": "status=running"
}
```
State is derived from replaying events.

### 25.4 Conflict Resolution
When conflicting events occur, priority order is:
1. cancellation events
2. user input events
3. tool results
4. background automation

### 25.5 State Snapshots
To avoid full replay, periodic snapshots are stored in SQLite; the event log continues after the snapshot.

---

## 26. Tool Dependency Graph (Execution DAG System)

### 26.1 Core Idea
Tools are nodes in a Directed Acyclic Graph (DAG).

### 26.2 Example
`fetch_file → parse → summarize → store_memory`

### 26.3 Tool Node Definition
```json
{
  "tool": "parse",
  "depends_on": ["fetch_file_1"],
  "inputs": {}
}
```

### 26.4 Execution Rules
* tools execute only when dependencies are complete
* DAG scheduler runs continuously in event loop
* partial failures propagate downstream

### 26.5 Retry Propagation
If node fails:
* downstream nodes are invalidated
* DAG re-evaluates execution path
* optional replan event emitted

---

## 27. Versioning & Compatibility System

### 27.1 Versioned Components
Astra explicitly versions:
* tool schemas
* memory schema
* prompt templates
* event formats
* state reducer logic

### 27.2 Version Format
`MAJOR.MINOR.PATCH`

### 27.3 Compatibility Rules
* **MAJOR** change → requires migration
* **MINOR** → backward compatible
* **PATCH** → safe hotfix

### 27.4 Migration System
On startup:
1. detect schema versions
2. run migration scripts
3. rebuild indexes if needed
4. validate state integrity

### 27.5 Safe Mode
If migration fails, fall back to last stable snapshot and disable non-critical tools.

---

## 28. Security Boundary Model (Trust Domains)

### 28.1 System Separation
Astra has strict trust layers:
* **Domain A: LLM Layer (Untrusted)**: reasoning, planning, tool selection.
* **Domain B: Runtime Core (Trusted)**: event loop, state reducer, permission enforcement.
* **Domain C: Tool Execution (Isolated)**: shell, IO, network, ML inference.
* **Domain D: Memory System (Semi-trusted)**: read/write controlled via policy.

### 28.2 Tool Restrictions
Tools CANNOT:
* mutate state directly
* call arbitrary other tools freely
* bypass permission engine
* escalate privileges

### 28.3 Memory Access Rules
Tools can only access memory via:
* read API (filtered)
* write API (validated)
* No raw filesystem access to vault.

### 28.4 Tool-to-Tool Calls
Allowed only through DAG scheduler. Direct tool chaining is forbidden.

---

## 29. System Boot Sequence (Initialization Model)

### 29.1 Boot Stages
1. **Stage 1: Core Runtime**: initialize event loop, initialize reducer, load config.
2. **Stage 2: Storage Layer**: load SQLite state DB, load event log, verify integrity.
3. **Stage 3: Memory System**: load Obsidian vault, rebuild vector index (incremental or full if needed).
4. **Stage 4: Tool Registry**: load tool schemas, validate versions, register permissions.
5. **Stage 5: Task Recovery**: restore incomplete tasks, reconstruct DAGs, resume background jobs if allowed.
6. **Stage 6: UI Activation**: start Astra HUD, attach event listeners, enable hotkey system.

### 29.2 Crash Recovery Boot
If crash detected:
1. replay event log from last snapshot
2. restore state deterministically
3. rehydrate active tasks
4. mark uncertain tools as “paused”

---

## 30. Deterministic vs Probabilistic Boundary (Critical Design Rule)

### 30.1 Deterministic Layer (NO LLM variability)
Must be fully predictable:
* event bus ordering
* state reducer logic
* permission checks
* tool execution scheduling
* DAG resolution
* persistence logic

### 30.2 Probabilistic Layer (LLM-driven)
Allowed to vary:
* intent classification
* reasoning steps
* planning strategies
* memory selection ranking
* tool choice proposals

### 30.3 Hard Rule
LLMs may propose actions — they cannot execute or finalize them.

### 30.4 Execution Firewall
Before any action:
`LLM → proposal → Runtime → validation → Event system → deterministic execution`

---

## 31. Formal Specification Layer (Machine-Readable Contracts)

### 31.1 Core Principle
All system components must have machine-enforceable definitions, not only descriptive text. Astra uses a hybrid of:
* JSON Schema (data contracts)
* Zod-like validation (runtime enforcement)
* Optional protobuf for high-performance channels

### 31.2 Component Specification Format
Every system component is defined as:
```json
{
  "name": "tool.run_shell",
  "version": "1.0.0",
  "input_schema": { },
  "output_schema": { },
  "side_effects": ["filesystem"],
  "permissions": "medium",
  "deterministic": true
}
```

### 31.3 Event Schema Contract
```json
{
  "event": "task.updated",
  "version": "1.0.0",
  "payload_schema": {},
  "ordering": "strict",
  "replayable": true
}
```

### 31.4 Enforcement Rule
If a component does not match its schema, it is rejected at runtime. No “best effort parsing”.

---

## 32. Scheduler Policy System

### 32.1 Core Problem
Multiple concurrent systems compete for:
* tool execution
* memory indexing
* LLM inference
* background automation

### 32.2 Scheduling Model
Astra uses a priority + fairness hybrid scheduler:

#### Priority levels
1. `USER_INTERACTIVE` (highest)
2. `INTERRUPT / CANCEL`
3. `TOOL_SYNC_EXECUTION`
4. `TOOL_ASYNC_EXECUTION`
5. `MEMORY_INDEXING`
6. `BACKGROUND_AUTOMATION` (lowest)

### 32.3 Fairness Rule
No class may starve others:
* background tasks get minimum guaranteed execution slices
* user tasks preempt all others
* long-running tasks are time-sliced

### 32.4 Starvation Prevention
If a task waits too long, the scheduler injects an execution window or temporarily boosts priority.

### 32.5 Preemption Model
Tasks are interruptible at safe checkpoints. Tool execution can be paused only if marked `interruptible: true`.

---

## 33. Resource Management Layer

### 33.1 Resource Types
Astra tracks:
* CPU usage per task
* RAM per worker
* disk IO quota
* GPU allocation (LLM inference)
* network bandwidth (optional tools)

### 33.2 Budget System
Each task receives a budget:
```json
{
  "cpu_ms": 2000,
  "memory_mb": 256,
  "io_ops": 1000,
  "gpu_ms": 0
}
```

### 33.3 Enforcement
Runtime enforces per-worker limits. Tasks exceeding budget are paused, downgraded, or terminated.

### 33.4 Global Resource Governor
A central controller prevents system overload, prioritizes interactive responsiveness, and throttles background agents dynamically.

---

## 34. System Invariants (Hard Guarantees)
These are non-negotiable correctness rules.

### 34.1 Core Invariants
* **I1 — State Determinism**: State is always derivable from event log.
* **I2 — No Direct State Mutation**: Only event reducer can modify state.
* **I3 — Tool Isolation**: Tools cannot modify system state directly.
* **I4 — Single Active Execution Path per Task**: A task cannot execute two conflicting branches simultaneously.
* **I5 — Event Ordering**: Events are processed in strict deterministic order.
* **I6 — Permission Precedence**: No execution occurs before permission validation.
* **I7 — Recoverability**: Every operation must be replayable from logs (unless explicitly marked non-replayable).

### 34.2 Invariant Enforcement
* validated at runtime
* checked during boot
* verified in debug mode via replay system

---

## 35. Cross-Session Identity Model

### 35.1 Identity Scope
Astra defines:
* user identity
* session identity
* task identity

### 35.2 User Identity
Persistent across all sessions:
* preferences
* memory association
* tool permissions
* personalization layer

Stored in: Obsidian vault + SQLite metadata.

### 35.3 Session Model
Each session has:
```json
{
  "session_id": "s123",
  "start_time": 0,
  "active_tasks": [],
  "context_snapshot": {}
}
```

### 35.4 Session Continuity Rules
On restart:
* active tasks restored if safe
* context rebuilt from memory
* UI state reset
* event log replayed

### 35.5 Multi-Session Conflict Resolution
If multiple sessions exist:
* most recent session is primary
* older sessions become read-only snapshots
* conflicting tasks are merged or paused

---

## 36. Security Audit & Observability Layer

### 36.1 Audit System Principle
Every sensitive action is logged immutably.

### 36.2 Audit Log Format
```json
{
  "timestamp": 0,
  "actor": "tool/run_shell",
  "action": "filesystem_write",
  "target": "/etc/config",
  "permission_decision": "denied",
  "reason": "high_risk_operation"
}
```

### 36.3 Coverage Requirements
Audit logs MUST include:
* tool invocations
* permission decisions
* system-level state changes
* escalation attempts
* failed security checks

### 36.4 Anomaly Detection Layer
Astra monitors unusual tool frequency, abnormal permission requests, unexpected system access patterns, and repeated failed executions. If detected, it flags the session, reduces permissions, or requires re-authorization.

### 36.5 Audit Replay Mode
Entire system behavior can be reconstructed by combining the event log and audit log. Full execution trace is replayable for debugging and forensic analysis.

---

## FINAL SYSTEM STATE (COMPLETE ARCHITECTURE)
At this point, Project Astra is fully specified as a verifiable distributed execution system for AI + tools + memory + OS control.

---

## 37. Execution Core (Formal Pseudocode Layer)
This defines the real runtime behavior of Astra.

### 37.1 Event Loop (Single Source of Truth)
```python
while true:
    event = EVENT_QUEUE.pop()
    
    if event is None:
        sleep()
    
    STATE = REDUCER(STATE, event)
    new_events = ROUTER(event, STATE)
    
    for e in new_events:
        EVENT_QUEUE.push(e)
```
**Key properties**:
* single-threaded authority
* deterministic ordering
* state only changes here
* everything else is event emission

### 37.2 Reducer Function (State Transition Engine)
```python
function REDUCER(state, event):
    switch event.type:
        case "task.created":
            state.tasks.add(event.task)
        case "task.updated":
            state.tasks[event.id].update(event.patch)
        case "tool.completed":
            state.tasks[event.task_id].mark_step_done()
        case "tool.failed":
            state.tasks[event.task_id].mark_error(event.error)
        case "context.updated":
            state.context.merge(event.data)
        case "memory.write":
            state.memory.store(event.entry)
        case "cancel":
            state.tasks[event.task_id].status = "cancelled"
    return state
```
**Rule**: reducer is PURE (no side effects).

### 37.3 Scheduler Algorithm
```python
function SCHEDULER(state):
    queue = sort_by_priority(state.tasks)
    for task in queue:
        if resource_budget_available(task) and not is_blocked(task):
            dispatch(task)
```
**Priority function**:
```python
priority = (user_interactive * 1000) + urgency_score - execution_time_penalty
```
**Starvation prevention**:
```python
if task.wait_time > threshold:
    priority += boost
```

### 37.4 DAG Execution Engine

#### DAG Construction
```python
function BUILD_DAG(llm_output):
    nodes = parse_tool_calls(llm_output)
    for node in nodes:
        node.dependencies = extract_dependencies(node)
    return nodes
```

#### Cycle Detection
```python
function HAS_CYCLE(dag):
    visited = set()
    stack = set()
    for node in dag:
        if dfs(node):
            return true
    return false

function dfs(node):
    if node in stack:
        return true
    if node in visited:
        return false
    stack.add(node)
    for dep in node.dependencies:
        if dfs(dep):
            return true
    stack.remove(node)
    visited.add(node)
    return false
```

#### DAG Execution Cycle
```python
function EXECUTE_DAG(dag):
    while not all_nodes_complete(dag):
        ready_nodes = [n for n in dag if n.dependencies_satisfied]
        for node in ready_nodes:
            dispatch_tool(node)
```

#### Incremental Update
```python
function UPDATE_DAG(existing_dag, new_nodes):
    merge_nodes(existing_dag, new_nodes)
    revalidate_dependencies()
    # re-run only affected subgraph
```

---

## 38. Error Propagation Model (Cross-Layer Failure System)

### 38.1 Error as Event
ALL errors are events:
```json
{
  "type": "tool.failed",
  "error": {
    "code": "TIMEOUT",
    "recoverable": true
  }
}
```

### 38.2 Propagation Chain
`Tool → Scheduler → Reducer → Planner → UI`

Each layer decides whether to:
* handle locally
* escalate
* retry
* replan

### 38.3 Layer Behavior
* **Tool Layer**: returns structured error.
* **Scheduler**: may reschedule or drop task.
* **Reducer**: updates task state.
* **Planner (LLM)**: generates new plan if needed.
* **UI**: displays failure or retry status.

### 38.4 Retry Backpressure Rules
```python
if retries > max:
    escalate_to_user()
elif system_overloaded:
    delay_retry()
else:
    retry_tool()
```

### 38.5 Error Classification
* `transient` → retry
* `deterministic` → replan
* `permission` → escalate
* `critical` → abort system action

---

## 39. Prompt → Event Translation Contract (Critical Missing Layer)
This defines how Astra turns raw text into structured execution.

### 39.1 Pipeline
`User Input (text) → Parser Layer → Intent Object → Event Generator → Event Bus`

### 39.2 Intent Parsing
```python
function PARSE(input):
    return {
        type: classify(input),
        entities: extract_entities(input),
        confidence: score(input)
    }
```

### 39.3 Event Generation
```python
function TO_EVENT(intent):
    if intent.type == "tool_request":
        return ToolCallEvent()
    if intent.type == "memory_request":
        return MemoryEvent()
    if intent.type == "chat":
        return ResponseEvent()
```

### 39.4 Validation Layer
```python
if event.schema_invalid:
    reject(event)
    request_repair_from_llm()
```

### 39.5 Repair Strategy
* attempt structured rewrite
* fallback to safe “ask clarification”
* never execute invalid events

---

## 40. Cold Start & Empty State Behavior

### 40.1 First Boot State
If system has no memory:
```python
state.memory = {}
state.tasks = []
state.context = minimal_system_prompt
```

### 40.2 Default Boot Context
Astra initializes with system identity, tool registry, safety policies, and a minimal operational prompt.

### 40.3 First Interaction Behavior
If no memory exists, do NOT assume user preferences; ask for clarification and rely purely on system rules.

### 40.4 Progressive Bootstrapping
As the user interacts, preferences are learned, memory is built incrementally, and the context becomes personalized over time.