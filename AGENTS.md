# AGENTS.md — Project Astra

## Architecture (what you need to know to navigate)

Three layers communicating over a Unix socket:

| Layer | Dir | Language | Role |
|-------|-----|----------|------|
| Core | `core/` | Rust | IPC server, event loop, SQLite log, tool execution, state reducer |
| Orchestrator | `orchestrator/` | Python | Agent loop, prompt construction, memory retrieval, LLM client |
| HUD | `hud/` | Tauri + React | Desktop overlay, user input, output display |

**IPC**: All components talk via `/tmp/astra.sock` using JSON-RPC 2.0 (newline-delimited JSON).
The Rust core is the server; the orchestrator and HUD are clients.

**Event flow**: `HUD → core (ui.input) → orchestrator (agent cycle) → core (tool.requested) → tool runner → core (tool.completed) → orchestrator → HUD (ui.output)`

## Build & run commands

```bash
# Rust core
cd core && cargo build          # edition = "2024" (requires nightly Rust)
cd core && cargo test           # runs all Rust unit tests

# Python orchestrator
cd orchestrator && python -m venv venv && source venv/bin/activate && pip install -e .
python orchestrator/main.py     # starts the agent loop (needs core running first)

# HUD
cd hud && npm install
npm run tauri dev               # Tauri dev shell (starts Vite + Tauri window)
npm run build                   # frontend-only build
```

**Startup order matters**: Core must be running before the orchestrator or HUD can connect.
The orchestrator polls for the socket for up to 10 seconds before giving up.

## Testing

```bash
# Rust unit tests (no external deps)
cd core && cargo test

# Python unit tests (no live runtime needed)
python -m unittest tests.test_memory_components tests.test_prompt_schema_client tests.test_agent_cycle

# E2E tests (require live core + orchestrator + LLM server)
python -m unittest tests.test_search_resilience
```

**Test isolation quirk**: Python tests import orchestrator modules by manipulating `sys.path` via
`tests/unit_test_helpers.py`. The `import_with_fake_faiss()` helper replaces the real `faiss`
module with a pure-NumPy fake so tests don't need FAISS installed. Always use these helpers
when writing new tests that touch orchestrator code.

## Hardcoded paths (must be aware of)

These are baked into source and will break if moved:

| Path | Where | Purpose |
|------|-------|---------|
| `/tmp/astra.sock` | `core/src/main.rs`, `orchestrator/main.py`, `hud/src-tauri/src/lib.rs`, `tests/e2e_runner.py` | IPC socket |
| `/tmp/astra.db` | `core/src/main.rs` | SQLite event log |
| `/home/jperez/Astra/memories` | `orchestrator/main.py` | Memory vault path |
| `/home/jperez/Astra/vault_memories.md` | `core/src/tools/runner.rs` | `save_memory` output file |
| `/home/jperez/.local/bin/astra-toggle` | `core/src/main.rs` | Resume script for Game Mode |

## LLM backend

Expects an OpenAI-compatible completions endpoint at `http://localhost:8080/v1/completions`.
The orchestrator uses ChatML format (`<|im_start|>` / `<|im_end|>`) for prompt construction.
Stop tokens: `<|im_end|>`, `<|endoftext|>`.

The `route_task()` function in `orchestrator/llm/client.py` currently ignores the task type
and always returns the same `LlamaClient`. Model routing is not yet implemented.

## Memory system

- Markdown files in `memories/` are parsed by paragraph chunks (`\n\n` splits)
- Embeddings use a **deterministic dummy embedder** (`DummyEmbedder`) — hash-based random vectors, not real embeddings
- FAISS `IndexFlatL2` for similarity search
- The embedder dimension defaults to 768 in `embedder.py` but the orchestrator `main.py` creates it with `dim=128`

## Tool system

Two tools registered in `orchestrator/tools/schema.py`:
- `run_shell(cmd)` — executes via `bash -c`, danger tier: medium
- `save_memory(content)` — appends to a markdown file, danger tier: low

Tool execution happens in the Rust core (`core/src/tools/runner.rs`). The orchestrator
extracts tool calls from the LLM response by regex-matching JSON blocks containing
`tool_name` and `args` keys.

## Game Mode (Hyprland-specific)

The core polls `hyprctl getoption animations:enabled` every 2 seconds. When animations
are disabled (Game Mode on), it emits `system.suspend` and kills: `llama-server`,
`orchestrator/main.py`, `astra-hud`, `smart-wallpaper-daemon`, `mpvpaper`, `ComfyUI`.
On resume, it runs `~/.local/bin/astra-toggle`.

## Safety / prompt guidelines

The system prompt in `orchestrator/llm/prompt.py` enforces:
- Search tools (`ls`, `find`, `cat`, `grep`) execute without confirmation
- Hidden files/dirs (starting with `.`) are blacklisted unless user explicitly requests them
- Destructive tools (`rm`, `mkdir`, `mv`, `write_file`) require explicit user confirmation
- Every modifying action must be verified with a follow-up observation
- Search resilience protocol: try `ls -la ~`, then `find ~ -maxdepth 2 -type d -iname "*keyword*"`, then translated variants

## Style & conventions

- Rust edition 2024 in `core/` (nightly-only feature)
- No formatter/linter config present (no `rustfmt.toml`, `.flake8`, etc.)
- No CI/CD workflows configured
- Python orchestrator uses `print()` for logging (no logging framework)
- Message history in the agent loop is pruned to last 20 messages
- The orchestrator's `main.py` has a startup fingerprint print for debugging

## Development workflow

When implementing new features or fixing bugs:
1. Make your changes following the existing architecture patterns
2. Run tests to ensure your changes don't break existing functionality
3. Commit your changes with a descriptive message
4. Push your changes to the remote repository

Commit messages should follow conventional commit style when possible (e.g., "feat: add new tool", "fix: resolve memory leak in IPC handler").