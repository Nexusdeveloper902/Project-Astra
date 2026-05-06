# Project Astra

Project Astra is a local-first, tool-augmented AI assistant designed as a lightweight personal operating layer for Linux systems. It provides a unified, context-aware interface for system automation, knowledge management, and persistent reasoning.

Unlike traditional chatbots, Astra is a modular cognitive system that combines memory, reasoning, tool execution, and state management into a single unified assistant layer.

## Core Design Philosophy

* **Minimal Friction**: Single global hotkey invocation (Super+Space) via an ephemeral overlay HUD.
* **Tool-First Intelligence**: All capabilities are exposed as structured tools, with the model deciding when to act versus respond.
* **Local-First Architecture**: Runs primarily on local hardware with support for high-performance GGUF models via llama.cpp.
* **Memory-Centric**: Long-term memory is managed via a vector-indexed Obsidian vault (RAG).

## System Architecture

Astra is composed of three primary layers communicating via a high-speed Unix Domain Socket event bus.

### 1. Astra Core (Rust)
The system runtime and security layer.
* Handles IPC communication via `/tmp/astra.sock`.
* Manages the global event bus and subsystem subscriptions.
* Executes system-level tools (shell, file I/O) with enforced safety boundaries.

### 2. Astra Orchestrator (Python)
The reasoning and agentic engine.
* Implements a stateful agentic loop with conversation history.
* Manages Retrieval-Augmented Generation (RAG) using FAISS and local embeddings.
* Orchestrates multi-step reasoning and command chaining.
* Communicates with LLM backends via OpenAI-compatible HTTP APIs.

### 3. Astra HUD (Tauri / React)
The user interface layer.
* Provides a keyboard-first, ephemeral overlay for user interaction.
* Visualizes tool execution status and memory retrievals.
* Centered, floating interface managed by Hyprland-specific window rules.
