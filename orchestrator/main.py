import json
import socket
import sys
import os
import time
import logging
import tomllib
import threading
from utils.parser import extract_tool_call, extract_text_response

from llm.prompt import construct_prompt
from llm.client import route_task
from llm.intent import generate_intent_contract
from tools.schema import registry
from memory.parser import parse_vault
from memory.embedder import DummyEmbedder, RealEmbedder
from memory.index import MemoryIndex
from events.schema import EventEnvelope

def load_config():
    config_path = os.path.expanduser("~/.config/astra/config.toml")
    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Failed to load config: {e}")
        return {}

config = load_config()
orchestrator_config = config.get("orchestrator", {})
core_config = config.get("core", {})

SOCKET_PATH = core_config.get("socket_path", "/tmp/astra.sock")
VAULT_PATH = orchestrator_config.get("vault_dir", "/home/jperez/Astra/memories")
LOG_LEVEL_STR = orchestrator_config.get("log_level", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL_STR.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(module)s: %(message)s"
)

logging.info("--- ASTRA STARTUP FINGERPRINT: 2026-05-06-15:38 ---")

def create_request(method, params, req_id):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params
    }

def emit_event(s, method, params):
    req = create_request(method, params, f"{method}_{int(time.time()*1000)}")
    s.sendall((json.dumps(req) + "\n").encode('utf-8'))

def run_agent_cycle(s, messages, embedder, index, llm_client, task_id="agent_loop"):
    """Executes one step of the agent reasoning loop."""
    active_context = {
        "cwd": os.getcwd(),
        "home": os.environ.get("HOME"),
        "user": os.environ.get("USER"),
        "app": "Astra HUD"
    }
    
    last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    
    # 3.2.2 Refined Intent Classification
    emit_event(s, "task.updated", {"type": "TaskUpdated", "task_id": task_id, "status": "classifying"})
    
    # Use classification-specific client
    classifier_client = route_task("classification")
    contract_data = generate_intent_contract(last_user_msg, classifier_client)
    
    emit_event(s, "intent.contracted", {
        "type": "IntentContracted",
        "task_id": task_id,
        "contract": contract_data
    })
    
    # 3.1.5 Retrieving State
    emit_event(s, "task.updated", {"type": "TaskUpdated", "task_id": task_id, "status": "retrieving"})
    q_vec = embedder.embed(last_user_msg)
    results = index.search(q_vec)
    # 3.1.6 Limit memory snippet length to prevent prompt bloat (approx 1500 tokens)
    MAX_MEM_CHARS = 6000
    retrieved_texts = []
    current_chars = 0
    if results:
        for r in results:
            text = r["text"]
            if current_chars + len(text) > MAX_MEM_CHARS:
                # Truncate if individual chunk is huge, or just stop adding chunks
                remaining = MAX_MEM_CHARS - current_chars
                if remaining > 100:
                    retrieved_texts.append(text[:remaining] + "... [truncated]")
                break
            retrieved_texts.append(text)
            current_chars += len(text)
    
    emit_event(s, "memory.retrieved", {
        "type": "MemoryRetrieved",
        "task_id": task_id,
        "memories": [{"text": t} for t in retrieved_texts]
    })
    
    # 3.1.6 Executing State
    emit_event(s, "task.updated", {"type": "TaskUpdated", "task_id": task_id, "status": "executing"})
    
    # Pass contract to the prompt
    active_context["intent"] = contract_data
    
    prompt = construct_prompt(
        messages=messages,
        active_context=active_context,
        memory_retrievals=retrieved_texts,
        tools=registry.get_all_tools(),
        task_state={"status": "executing"}
    )
    
    logging.debug(f"\n--- AGENT PROMPT ---\n{prompt}\n--- END PROMPT ---\n")
    logging.info("--- AGENT CYCLE ---")
    
    # Emit execution context
    routing_decision = contract_data.get("task_type", "reasoning")
    reasoning_client = route_task(routing_decision)
    
    emit_event(s, "execution.context_captured", {
        "type": "ExecutionContextCaptured",
        "context_id": f"ctx_{int(time.time())}",
        "session_id": "default",
        "task_id": task_id,
        "model_id": "llama-default",
        "temperature": reasoning_client.default_params["temperature"],
        "max_tokens": reasoning_client.default_params["max_tokens"],
        "prompt_template_version": "v1",
        "tool_registry_version": "v1",
        "planner_version": "v1",
        "routing_decision": routing_decision,
        "retrieved_memory_ids": [] 
    })
    
    llm_response = reasoning_client.generate(prompt)
    logging.info(f"Assistant: {llm_response}")
    
    messages.append({"role": "assistant", "content": llm_response})
    
    try:
        parsed_tool, error_reason = extract_tool_call(llm_response, registry)
        
        # Check for textual response indicating conversational reply
        clean_text = extract_text_response(llm_response)
        
        if clean_text:
            res = create_request("ui.output", {
                "type": "UiOutput",
                "text": clean_text
            }, f"ui_{int(time.time())}")
            s.sendall((json.dumps(res) + "\n").encode('utf-8'))

        if parsed_tool:
            args_str = json.dumps(parsed_tool['args'])
            status_text = f"[Executing: {parsed_tool['name']} {args_str}]"
            
            status_msg = create_request("ui.output", {
                "type": "UiOutput",
                "text": status_text
            }, f"st_{int(time.time())}")
            s.sendall((json.dumps(status_msg) + "\n").encode('utf-8'))
            
            req = create_request("tool.requested", {
                "type": "ToolRequest",
                "task_id": task_id,
                "tool_name": parsed_tool["name"],
                "args": parsed_tool["args"],
                "danger_tier": "medium" if parsed_tool["name"] == "run_shell" else "low"
            }, f"req_{int(time.time())}")
            s.sendall((json.dumps(req) + "\n").encode('utf-8'))
            
        elif error_reason and "No JSON blocks found" not in error_reason:
            # Emit tool.rejected for invalid tool attempts
            logging.warning(f"Tool rejected: {error_reason}")
            rej = create_request("tool.rejected", {
                "type": "ToolRejected",
                "task_id": task_id,
                "tool_name": "unknown",
                "reason": error_reason
            }, f"rej_{int(time.time())}")
            s.sendall((json.dumps(rej) + "\n").encode('utf-8'))
            
            # Feed the rejection back to the LLM immediately to attempt a replan
            messages.append({"role": "system", "content": f"Tool call validation failed: {error_reason}"})
            if len(messages) > 20: messages = messages[-20:]
            run_agent_cycle(s, messages, embedder, index, llm_client, task_id)
        else:
            # No tool call found, assume task completed or just chat
            emit_event(s, "task.completed", {
                "type": "TaskCompleted",
                "task_id": task_id,
                "result": {"text": clean_text}
            })

    except Exception as e:
        logging.error(f"Cycle Error: {e}")

def main():
    logging.info("Astra Orchestrator initialized.")
    
    docs = parse_vault(VAULT_PATH)
    
    memory_config = config.get("memory", {})
    embedder_type = memory_config.get("embedder_type", "sentence-transformers")
    embedder_model = memory_config.get("embedder_model", "all-MiniLM-L6-v2")
    # Real embeddings (all-MiniLM-L6-v2) have dim 384, Dummy uses 128
    embedder_dim = memory_config.get("embedder_dim", 384 if embedder_type == "sentence-transformers" else 128)
    
    if embedder_type == "dummy":
        embedder = DummyEmbedder(dim=embedder_dim)
    else:
        embedder = RealEmbedder(model_name=embedder_model)
    
    # 2. Build Memory Index
    index = MemoryIndex(dim=embedder.dim)
    
    vault_dir = "/home/jperez/Astra/memories"
    vault_file = "/home/jperez/Astra/vault_memories.md"
    
    all_docs = []
    # 1. Load from dedicated memories directory
    if os.path.exists(vault_dir):
        all_docs.extend(parse_vault(vault_dir))
    
    # 2. Load the specific auto-vault file
    if os.path.exists(vault_file):
        with open(vault_file, 'r', encoding='utf-8') as f:
            content = f.read()
            chunks = [c.strip() for c in content.split('\n\n') if c.strip()]
            for i, chunk in enumerate(chunks):
                all_docs.append({
                    "id": f"vault_{i}",
                    "text": chunk,
                    "source": vault_file
                })
    
    if all_docs:
        logging.info(f"Indexing {len(all_docs)} memory chunks...")
        texts = [d["text"] for d in all_docs]
        index.add(embedder.embed_batch(texts), all_docs)
        
    llm_client = route_task("reasoning") # Default client


    
    logging.info(f"Connecting to {SOCKET_PATH}...")
    for _ in range(20):
        if os.path.exists(SOCKET_PATH): break
        time.sleep(0.5)
    else:
        sys.exit(1)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        try:
            s.connect(SOCKET_PATH)
            logging.info("Connected. Ready for Agentic Loops.")
            
            # 3.1.2 Set system status to idle
            emit_event(s, "task.updated", {"type": "TaskUpdated", "task_id": "system", "status": "idle"})
            
            buffer = ""
            messages = []
            while True:
                data = s.recv(4096)
                if not data: break
                    
                buffer += data.decode('utf-8')
                lines = buffer.split('\n')
                buffer = lines.pop()
                
                for line in lines:
                    if not line.strip(): continue
                    logging.debug(f"Received raw line: {line}")
                    
                    # Skip JSON-RPC responses (they don't have 'event' field)
                    if '"result":' in line or '"error":' in line:
                        continue

                    try:
                        envelope = EventEnvelope.model_validate_json(line)
                    except Exception as e:
                        logging.error(f"Schema validation failed for event: {e}")
                        continue
                    
                    if envelope.event == "ui.input":
                        user_text = envelope.data.text
                        messages.append({"role": "user", "content": user_text})
                        if len(messages) > 20: messages = messages[-20:]
                        
                        # 3.1.1 Create Task and start pipeline
                        task_id = f"task_{int(time.time())}"
                        emit_event(s, "task.created", {"type": "TaskCreated", "task_id": task_id, "goal": user_text})
                        
                        threading.Thread(target=run_agent_cycle, args=(s, messages, embedder, index, llm_client, task_id), daemon=True).start()
                        
                    elif envelope.event == "tool.completed":
                        res_data = envelope.data.result
                        summary = json.dumps(res_data)
                        if len(summary) > 500: summary = summary[:500] + "... [truncated]"
                        
                        messages.append({"role": "system", "content": f"Tool completed. Result: {summary}"})
                        if len(messages) > 20: messages = messages[-20:]
                        
                        threading.Thread(target=run_agent_cycle, args=(s, messages, embedder, index, llm_client, envelope.data.task_id), daemon=True).start()
                        
                    elif envelope.event == "memory.retrieved":
                        # We just log this for observability. 
                        # Memory is already injected into the prompt synchronously in run_agent_cycle.
                        docs = envelope.data.memories
                        logging.info(f"Retrieved {len(docs)} memories.")
                        
                    elif envelope.event == "tool.rejected":
                        err = envelope.data.reason
                        messages.append({"role": "system", "content": f"Tool failed: {err}"})
                        if len(messages) > 20: messages = messages[-20:]
                        
                        threading.Thread(target=run_agent_cycle, args=(s, messages, embedder, index, llm_client, envelope.data.task_id), daemon=True).start()

        except Exception as e:
            logging.error(f"Runtime Error: {e}")

if __name__ == "__main__":
    main()
