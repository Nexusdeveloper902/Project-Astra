# Project Astra

Final Consolidated System Design and Technical Specification, v0.1.

This document consolidates the full revised Astra architecture, runtime contracts, security model, execution semantics, and implementation stack into one coherent master specification. It is intended to be the build-level reference for a local-first AI assistant kernel on Linux.

# 1. Purpose and Scope

Project Astra is a local, tool-augmented AI assistant designed to function as a lightweight personal operating layer over a Linux system. Its purpose is to provide fast, context-aware interactions; automate tasks; manage knowledge; and act as a unified interface between the user and their environment.

Astra is not a chatbot. It is a modular cognitive system combining memory, reasoning, tool execution, context awareness, and explicit state management into a single assistant layer.

* Local-first and Linux-first by design.
* Tool execution is first-class, not optional.
* All important state changes are event-driven and replayable.
* The LLM proposes actions; the runtime validates and executes them.

# 2. Core Design Philosophy

## 2.1 Minimal Friction Interaction

* Single global hotkey invocation.
* Ephemeral overlay UI instead of full app switching.
* Automatic intent inference with no manual mode selection.

## 2.2 Tool-First Intelligence

* All capabilities are exposed as tools.
* The model decides when to act versus respond.
* Execution is treated as a first-class capability.

## 2.3 Local-First Architecture

* Runs primarily on local hardware.
* Offline-capable core system.
* External APIs are optional modules, not dependencies.

## 2.4 Memory as a First-Class System

* Long-term memory stored in an Obsidian vault.
* Retrieval-Augmented Generation (RAG) for context injection.
* Automatic capture of useful knowledge with provenance.

# 3. High-Level Architecture

Astra is composed of layered subsystems that communicate through explicit contracts.

## 3.1 Interaction Layer

* Global hotkey trigger.
* Ephemeral overlay (Astra HUD).
* Text input and optional voice input.
* Context injection from clipboard, selection, and active application.

## 3.2 Intent Processing Layer

* Classifies input into conversational response, tool execution, memory operation, or multi-step task planning.
* Produces structured intent objects.

## 3.3 Core Reasoning Engine

* Local LLM routed by task type and complexity.
* Handles planning, decomposition, and reasoning.
* Selects appropriate tools and memory.

## 3.4 Tool Execution Layer (Astra Runtime)

* Executes system actions and subprocesses.
* Interfaces with the Linux system and Hyprland.
* Enforces permissions, capability checks, and sandboxing.

## 3.5 Memory System (Astra Vault)

* Obsidian-based structured knowledge base.
* Vector index for semantic retrieval.
* Automatic ingestion pipeline with ranking and conflict handling.

## 3.6 Context Awareness Layer

* Active window tracking.
* Clipboard monitoring.
* Selection capture.
* Project-aware context injection.

# **4\. Core Execution Pipeline**

Astra operates through a structured loop:

**Capture \-\> Classify \-\> Retrieve \-\> Plan \-\> Decide \-\> Act \-\> Validate \-\> Store \-\> Feedback**

* Capture: collect user input and system context.  
* Classify: determine the intent type.  
* Retrieve: pull relevant memory and context.  
* Plan: build an action or response plan.  
* Decide: choose execution path.  
* Act: execute tools or generate output.  
* Validate: verify outputs and state changes.  
* Store: save relevant memory and logs.  
* Feedback: feed results into recovery and learning loops.

# **5\. Tool System**

## **5.1 Tool Definition Schema**

* name  
* description  
* input\_schema  
* output\_schema  
* permission\_level  
* side\_effects  
* timeout\_ms  
* danger\_tier (low / medium / high / critical)

## **5.2 Invocation Contract**

* tool name  
* arguments (JSON)  
* request ID  
* session context  
* confirmation flag when required

## **5.3 Permission System**

* Low-risk tools: automatic execution.  
* Medium-risk tools: contextual validation.  
* High-risk tools: explicit user confirmation.  
* Critical tools: blocked until explicit approval.

Permissions are enforced before execution, not after.

## **5.4 Output Validation**

* Schema validation of outputs.  
* Size limits and truncation rules.  
* Structured error normalization.  
* Safety filtering of sensitive outputs.

## **5.5 Failure Propagation**

* Error type, message, retryability, suggested fix, and safe stack trace.  
* Failures feed retry logic, fallback tools, user escalation, and debugging mode.

# **6\. Memory System \- Astra Vault**

## **6.1 Storage Structure**

* Obsidian markdown vault.  
* Organized into Projects, Concepts, Logs, and System Notes.

## **6.2 Memory Granularity**

* Primary: note-level storage.  
* Secondary: chunk/paragraph-level indexing.  
* Chunks retain context and metadata.

## **6.3 Embeddings and Indexing**

* Embeddings are generated per chunk.  
* Vector index is stored separately.  
* Supports fast semantic search and incremental updates.  
* Metadata tracks timestamps, tags, source file, and confidence score.

## **6.4 Memory Types**

* Explicit user notes.  
* Auto-captured insights.  
* Task history.  
* Preferences.  
* Procedural knowledge.

## **6.5 Write Policy**

* Store stable facts, workflows, and preferences.  
* Ignore transient chatter, noise, and duplicates.  
* Prefer summaries over raw logs.  
* Attach provenance to every entry.

## **6.6 Conflict Resolution**

* Prefer newer information when it is time-sensitive.  
* Prefer explicit user statements.  
* Preserve conflicting entries when uncertain.  
* Mark outdated entries as superseded instead of deleting them.

## **6.7 Retrieval Policy**

* Semantic search first.  
* Keyword fallback second.  
* Context-scoped retrieval preferred.  
* Rank by relevance, recency, and confidence.

# **7\. Model Routing System**

## **7.1 Inputs to Routing**

* Task type.  
* Input length.  
* Context size.  
* Latency budget.  
* Tool likelihood.  
* Reasoning complexity.  
* Classification confidence.

## **7.2 Model Tiers**

* Small model: classification, extraction, quick replies.  
* Medium model: general reasoning and tool planning.  
* Large model: deep reasoning, architecture, and complex coding.

## **7.3 Routing Logic**

* Heuristic rules for obvious cases.  
* Lightweight classifier for ambiguity.  
* Confidence threshold escalation.

## **7.4 Fallback Policy**

* Escalate if uncertain.  
* Retry on failure.  
* Never block the user response entirely.

## **7.5 Cost Strategy**

* Prefer the smallest sufficient model.  
* Reserve large models for complex tasks.  
* Optimize for responsiveness.

# **8\. User Interface \- Astra HUD**

* Minimal overlay interface.  
* Keyboard-first interaction.  
* Optional voice input.  
* Shows the input box, active context, tool execution status, and memory suggestions.

# **9\. Automation Layer**

## **9.1 Autonomy Levels**

* L0: suggestions only.  
* L1: requires confirmation.  
* L2: limited autonomous execution.  
* L3: supervised multi-step automation.

## **9.2 Task Tracking System**

* Task ID.  
* Goal.  
* Current step.  
* Status.  
* Retries.  
* Pending actions.  
* Cancellation flag.

## **9.3 Cancellation Model**

* The user can interrupt at any time.  
* Future actions stop immediately.  
* Partial progress is preserved when possible.

## **9.4 Background Tasks**

* Visible task registry.  
* Resumable execution.  
* Scoped to goals.  
* Bound by safety rules.

# **10\. Context Awareness**

## **10.1 Signals**

* Active window.  
* Clipboard.  
* Selection.  
* Project directory.  
* Optional screenshots with opt-in.

## **10.2 Sampling Strategy**

* Event-driven capture rather than constant polling.  
* Deduplication of repeated signals.  
* Rate limiting for noisy sources.

## **10.3 Relevance Filtering**

* Only meaningful context is retained.  
* Transient data is treated as ephemeral.  
* Summaries are preferred over raw capture.

## **10.4 Privacy Model**

* Fully local by default.  
* Sensitive data is not persisted unless required.  
* Capture and storage boundaries are explicit.

# **11\. Security Model**

## **11.1 Sandboxing**

* Restricted shell execution.  
* Isolated subprocesses.  
* Controlled file access.

## **11.2 Confirmation Rules**

* Destructive operations.  
* System changes.  
* Network-sensitive actions.  
* Privilege escalation.  
* High-risk automation.

## **11.3 Danger Tiers**

* Low: safe and reversible.  
* Medium: limited impact.  
* High: system-altering.  
* Critical: potentially destructive.

## **11.4 Escalation Policy**

* No automatic privilege escalation.  
* Explicit user approval is required.

# **12\. Extensibility**

* Modular tool system.  
* Pluggable memory systems.  
* Swappable model backends.  
* Replaceable UI layers.  
* Versioned policy engine.

# **13\. System State Model**

## **13.1 State Objects**

* Task stack.  
* Active goal.  
* Pending tools.  
* Memory set.  
* Context window.  
* Confirmation queue.  
* Interruption state.

## **13.2 State Machine**

* idle  
* capturing  
* classifying  
* retrieving  
* planning  
* executing  
* waiting\_confirmation  
* recovering  
* completed  
* cancelled

## **13.3 Interruption Handling**

* Any user input interrupts execution.  
* State is preserved where possible.  
* Tasks can resume after interruption.

# **14\. Technical Implementation Stack**

Astra is implemented as a split-runtime system: Rust for the deterministic core and Python for orchestration.

## **14.1 Target Environment**

* Linux primary target.  
* Arch Linux target environment.  
* Hyprland-compatible window manager.  
* Hardware assumption: Ryzen 5 5600G or better, AMD RX 9060 XT 16 GB VRAM, 16-32 GB RAM.

## **14.2 Core Language Stack**

* Rust: event bus, scheduler, reducer, tool runtime, sandbox controller.  
* Python 3.11+: LLM routing, prompt orchestration, memory indexing logic, tool definitions.  
* Tauri: Astra HUD.  
* Bash and Python for controlled tool scripts.

## **14.3 Runtime Architecture**

* Rust is the deterministic event loop and authority.  
* Python is the reasoning and orchestration layer.  
* Workers are isolated tool executors.

## **14.4 Model Stack**

* Reasoning model: Qwen2.5-14B-Instruct Q6\_K, fallback Qwen2.5-7B-Instruct.  
* Fast model: Qwen2.5-3B-Instruct or Phi-3 Mini.  
* Embedding model: BGE-M3 preferred, e5-large-v2 as fallback.  
* llama.cpp is the primary runtime backend, with ROCm or Vulkan acceleration if available.

# **15\. Execution Boundary Contract (Rust \<-\> Python IPC)**

Astra uses strict JSON-RPC 2.0 over a Unix socket with no deviations.

## **15.1 Connection Ordering**

* FIFO ordering per IPC connection.  
* Per-connection order is preserved.  
* Cross-connection messages are arbitrated by the Rust event loop.

## **15.2 Backpressure Model**

* Each IPC connection has a bounded input queue.  
* Default max\_queue\_size is configurable, with a default of 1024\.  
* Blocking mode is the default; reject mode may return BACKPRESSURE\_LIMIT.

## **15.3 Request Format**

{  
  "jsonrpc": "2.0",  
  "id": "call\_123",  
  "method": "tool.execute",  
  "params": {  
    "tool": "run\_shell",  
    "args": {  
      "cmd": "ls \-la"  
    },  
    "context": {  
      "task\_id": "t1"  
    }  
  }  
}

## **15.4 Response Format**

{  
  "jsonrpc": "2.0",  
  "id": "call\_123",  
  "result": {  
    "output": "...",  
    "status": "success"  
  }  
}

* Malformed messages are rejected immediately.  
* No best-effort parsing.  
* Invalid RPC frames do not enter the event system.

# **16\. Capability-Based Security Model**

Permission tiers are replaced by enforceable capability tokens.

## **16.1 Tool Execution Levels**

* Level 0: safe memory reads, file reads, metadata queries.  
* Level 1: restricted file writes in a sandbox directory, subprocess execution, bounded I/O.  
* Level 2: dangerous system commands and filesystem-wide operations requiring explicit approval token.  
* Level 3: blocked by default, including network access and privilege escalation.

## **16.2 Capability Token Structure**

{  
  "token\_id": "cap\_abc123",  
  "task\_id": "t1",  
  "tool": "run\_shell",  
  "capabilities": \[  
    "fs\_read",  
    "process\_spawn"  
  \],  
  "issued\_at": 1710000000,  
  "expires\_at": 1710000060,  
  "origin": "user\_approval",  
  "signature": "ed25519\_signature"  
}

## **16.3 Validation and Revocation**

* Tokens are task-bound, tool-bound, time-limited, and scope-limited.  
* Validation occurs at execution start and again at commit boundary.  
* Revoked tokens cannot authorize future tool execution.  
* Queued tool executions using revoked tokens are dropped.  
* In-flight results are discarded at the commit boundary if the token was revoked.

# **17\. Scheduler Semantics**

* Rust event loop is non-preemptive.  
* Tools are preemptive and killable at safe boundaries.  
* Python is cooperative and event-driven only.  
* Preemption is allowed only between tool invocations.  
* Reducer execution is never interrupted.

## **17.1 Scheduler Policy**

* Priority and fairness hybrid scheduling.  
* Priority order: USER\_INTERACTIVE, INTERRUPT / CANCEL, TOOL\_SYNC\_EXECUTION, TOOL\_ASYNC\_EXECUTION, MEMORY\_INDEXING, BACKGROUND\_AUTOMATION.  
* No class may starve other classes.  
* Long-running tasks are time-sliced.  
* Stuck tasks are detected and escalated.

# **18\. Memory Compiler Pipeline**

## **18.1 Write Pipeline**

Raw Input  
 \-\> Normalize  
 \-\> Deduplicate  
 \-\> Conflict Detection  
 \-\> Chunk  
 \-\> Embed  
 \-\> Index

## **18.2 Ranking Function**

score \=  
    0.45 \* similarity  
  \+ 0.25 \* recency  
  \+ 0.15 \* frequency  
  \+ 0.15 \* task\_overlap

* Weights are stored in config, hot-reloadable, and versioned alongside the memory schema.  
* Index updates are asynchronous.  
* Read operations use the last stable snapshot.  
* Writes never block reads.

## **18.3 Embedding Stability**

* Every vector stores model name and version.  
* Only embeddings from the same model version are compared.  
* FAISS indexes are partitioned by embedding model and version.  
* If the model changes, a new index is created and the old one is preserved.

# **19\. Event Bus Architecture**

* All subsystems communicate via events.  
* The event bus is asynchronous, but the state reducer is authoritative.  
* Components subscribe to event types rather than mutating shared state.

## **19.1 Event Types**

* Input events: user.input, ui.command, hotkey.trigger.  
* System events: context.updated, memory.retrieved, tool.requested, tool.completed, tool.failed.  
* Task events: task.created, task.updated, task.completed, task.failed, task.cancelled.

# **20\. Persistent Storage Architecture**

* Obsidian vault for human-readable memory.  
* SQLite for task state, tool logs, event history, and session state.  
* FAISS for vector search and semantic similarity.

## **20.1 Backup Strategy**

* Obsidian is git-backed.  
* SQLite is periodically snapshotted.  
* Vector DB is regenerable from notes.

# **21\. Prompt Orchestration Layer**

Python builds the final prompt using structured blocks and explicit token budgeting.

## **21.1 Prompt Structure**

* System core instruction.  
* User input.  
* Active context.  
* Memory retrievals.  
* Tool schema definitions.  
* Task state.  
* Recent tool results.

## **21.2 Context Compression**

* Summarize conversation when token budget approaches limits.  
* Retain open tasks, unresolved tool results, and active goals.  
* Use a sliding window strategy for dialogue history.

# **22\. UI Contract (Astra HUD)**

* UI emits ui.input and ui.cancel events.  
* Tool progress, memory retrievals, and partial outputs stream back to the HUD.  
* A cancel event stops future tool execution, flags the task cancelled, and emits task.cancelled.

# **23\. Observability and Logging**

* Structured logs for system, tool, memory, model, and event activity.  
* Tool execution traces capture input, output, latency, and status.  
* Replay system can reconstruct a session from event and audit logs.  
* Metrics include tool success rate, average latency, memory retrieval hit rate, task completion rate, and failure clustering.

# **24\. Recovery and Repair System**

* Recovery triggers include tool failure, invalid output, timeout, model uncertainty, and state inconsistency.  
* Recovery actions include retry, fallback, replan, and escalate.  
* Partial rollback preserves valid earlier steps and rewinds to the last stable checkpoint.  
* Branching recovery can preserve Plan A and explore Plan B.

# **25\. Concurrency Model and Canonical State Store**

* Hybrid single-event-loop plus worker-pool model.  
* Only the event loop may mutate state.  
* Workers execute tools and return results, but never modify shared state.  
* The event-sourced reducer is the single authority for state mutation.  
* State is derived from replaying the event log and periodic snapshots are stored in SQLite.

## **25.1 Async Safety Invariant**

* All async subsystems are event emitters only.  
* They may emit completion, error, and progress events.  
* They may not mutate state, bypass the reducer, or modify scheduler state.

# **26\. Tool Dependency Graph (DAG) System**

* Tools are nodes in a directed acyclic graph.  
* Tools execute only when dependencies are complete.  
* Partial failures invalidate downstream nodes and may trigger replan.  
* DAG changes are revalidated incrementally.

fetch\_file \-\> parse \-\> summarize \-\> store\_memory

# **27\. Versioning and Compatibility**

* Tool schemas, memory schema, prompt templates, event formats, and reducer logic are versioned.  
* Semantic versioning is used: MAJOR.MINOR.PATCH.  
* MAJOR changes require migration.  
* MINOR changes are backward compatible.  
* PATCH changes are safe hotfixes.  
* On startup, Astra detects versions, runs migrations, rebuilds indexes if needed, and validates integrity.  
* If migration fails, the system falls back to the last stable snapshot and disables non-critical tools.

# **28\. Trust Domains and Boot Sequence**

## **28.1 Trust Domains**

* Domain A: LLM layer (untrusted).  
* Domain B: Runtime core (trusted).  
* Domain C: Tool execution (isolated).  
* Domain D: Memory system (semi-trusted, policy-mediated).

## **28.2 Boot Stages**

* Stage 1: initialize event loop, reducer, and config.  
* Stage 2: load SQLite state DB and event log, verify integrity.  
* Stage 3: load Obsidian vault and rebuild vector index.  
* Stage 4: load tool schemas, versions, and permissions.  
* Stage 5: restore incomplete tasks and reconstruct DAGs.  
* Stage 6: activate the HUD, event listeners, and hotkey system.

# **29\. Deterministic vs Probabilistic Boundary**

* Deterministic layer: event ordering, reducer logic, permission checks, tool scheduling, DAG resolution, persistence.  
* Probabilistic layer: intent classification, reasoning steps, planning strategies, memory selection ranking, tool choice proposals.  
* LLMs may propose actions, but they cannot execute or finalize them.  
* The runtime validates proposals and the event system performs deterministic execution.

# **30\. Formal Specification Layer**

* All components are machine-enforceable, not just described in prose.  
* JSON Schema is used for data contracts.  
* Zod-like validation is used at runtime.  
* Protobuf can be added later for high-performance channels.  
* Malformed components are rejected at runtime without best-effort parsing.

# **31\. System Invariants**

* State determinism: state is always derivable from the event log.  
* No direct state mutation outside the reducer.  
* Tool isolation: tools cannot mutate system state directly.  
* Single active execution path per task.  
* Strict event ordering.  
* Permission precedence before execution.  
* Recoverability for all replayable operations.

# **32\. Cross-Session Identity Model**

* User identity persists across sessions.  
* Session identity scopes active tasks and context snapshots.  
* Task identity tracks individual work items.  
* On restart, safe active tasks are restored, context is rebuilt from memory, UI state is reset, and the event log is replayed.  
* The most recent session is primary; older sessions become read-only snapshots.

# **33\. Security Audit and Anomaly Detection**

* Every sensitive action is logged immutably.  
* Audit logs include tool invocations, permission decisions, state changes, escalation attempts, and failed security checks.  
* The system monitors unusual tool frequency, abnormal permission requests, unexpected access patterns, and repeated failed executions.  
* Suspicious sessions are flagged, permissions are reduced, or re-authorization is required.  
* Event log plus audit log supports full forensic replay.

# **34\. Execution Core (Formal Pseudocode Layer)**

## **34.1 Event Loop**

while true:  
    event \= EVENT\_QUEUE.pop()

    if event is None:  
        sleep()

    STATE \= REDUCER(STATE, event)  
    new\_events \= ROUTER(event, STATE)

    for e in new\_events:  
        EVENT\_QUEUE.push(e)

The event loop is the single source of truth. State changes only here.

## **34.2 Reducer**

function REDUCER(state, event):  
    switch event.type:  
        case "task.created":  
            state.tasks.add(event.task)  
        case "task.updated":  
            state.tasks\[event.id\].update(event.patch)  
        case "tool.completed":  
            state.tasks\[event.task\_id\].mark\_step\_done()  
        case "tool.failed":  
            state.tasks\[event.task\_id\].mark\_error(event.error)  
        case "context.updated":  
            state.context.merge(event.data)  
        case "memory.write":  
            state.memory.store(event.entry)  
        case "cancel":  
            state.tasks\[event.task\_id\].status \= "cancelled"  
    return state

## **34.3 Scheduler**

function SCHEDULER(state):  
    queue \= sort\_by\_priority(state.tasks)  
    for task in queue:  
        if resource\_budget\_available(task) and not is\_blocked(task):  
            dispatch(task)

## **34.4 DAG Execution Engine**

function BUILD\_DAG(llm\_output):  
    nodes \= parse\_tool\_calls(llm\_output)  
    for node in nodes:  
        node.dependencies \= extract\_dependencies(node)  
    return nodes

## **34.5 Error Propagation Model**

* Tool \-\> Scheduler \-\> Reducer \-\> Planner \-\> UI.  
* Errors are first-class events.  
* Transient errors retry, deterministic errors replan, permission errors escalate, and critical errors abort the action.

# **35\. Execution Semantics Contract**

The ESC defines the formal meaning of execution, progress, and completion.

## **35.1 Task Definition**

* Task \= (Event Log, Derived State, Goal Predicate).  
* Event Log is immutable truth.  
* Derived State is reducer(E).  
* Goal is a pure function over committed derived state only.

## **35.2 Completion Semantics**

* A task is complete iff Goal(State\_committed) \== TRUE.  
* DAG completion, absence of events, and system idle state are not completion criteria.  
* Those are structural invariants, not semantic completion.

## **35.3 Progress Model**

* Progress is not scalar.  
* Progress is a partial order over valid goal states.  
* The system must never regress in goal space.

## **35.4 Semantic Stability Axiom**

* Goal(State) must be invariant under any causally valid event reordering.  
* This guarantees replay determinism, scheduler independence, and concurrency safety.

## **35.5 Final Kernel Truth**

* The event log is the only authoritative system state.  
* Memory vault, FAISS index, Python state, and tool outputs are derived or observed views.

# **36\. Final Summary**

Project Astra is a local-first intelligent assistant system built around tool-based execution, persistent semantic memory, context-aware reasoning, dynamic model routing, explicit state management, strict safety boundaries, and a formally defined execution semantics contract.

At the implementation level, Astra is a deterministic event-sourced capability kernel with a probabilistic planning front-end. Rust is the authority and runtime kernel. Python is the cognitive orchestration layer. Tools are isolated executors. Memory is a versioned semantic store. The event log is the single source of truth.

This architecture prioritizes determinism, local execution, modularity, safe tool execution, replayability, and scalable agent behavior.
