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

## Installation and Setup

### Prerequisites
* **LLM Backend**: `llama.cpp` server running locally (recommended port: 8080).
* **Rust**: Required for Astra Core and HUD.
* **Python 3.12+**: Required for the Orchestrator.
* **Node.js / npm**: Required for building the HUD.

### 1. LLM Model Hosting
Astra is optimized for Qwen 2.5 14B or similar models.
```bash
# Run with ROCm/CUDA acceleration and ChatML support
llama-server -m /path/to/model.gguf -ngl 99 -c 4096 --port 8080
```

### 2. Orchestrator Setup
```bash
cd orchestrator
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Astra Core
```bash
cd core
cargo build --release
```

### 4. HUD UI
```bash
cd hud
npm install
npm run tauri build
```

## Usage

### Invocation
The system is designed to be triggered via a global hotkey.
* **Default Hotkey**: `Super + Space` (configured in Hyprland).
* **Toggle Script**: `~/.local/bin/astra-toggle` handles the synchronized startup of all subsystems.

### Interaction Protocol
Astra uses the **ChatML** format for all internal reasoning. Users can provide natural language commands which are then decomposed into tool calls or conversational responses.
