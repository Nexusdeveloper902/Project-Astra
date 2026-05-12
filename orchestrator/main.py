import json
import socket
import sys
import os
import time
import logging
import tomllib
from utils.parser import extract_tool_call, extract_text_response

from llm.prompt import construct_prompt
from llm.client import route_task
from tools.schema import registry
from memory.parser import parse_vault
from memory.embedder import DummyEmbedder, RealEmbedder
from memory.index import MemoryIndex

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

def run_agent_cycle(s, messages, embedder, index, llm_client):
    """Executes one step of the agent reasoning loop."""
    active_context = {
        "cwd": os.getcwd(),
        "home": os.environ.get("HOME"),
        "user": os.environ.get("USER"),
        "app": "Astra HUD"
    }
    
    last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    q_vec = embedder.embed(last_user_msg)
    results = index.search(q_vec, k=2)
    retrieved_texts = [r["text"] for r in results] if results else []
    
    prompt = construct_prompt(
        messages=messages,
        active_context=active_context,
        memory_retrievals=retrieved_texts,
        tools=registry.get_all_tools(),
        task_state={"status": "processing"}
    )
    
    logging.debug(f"\n--- AGENT PROMPT ---\n{prompt}\n--- END PROMPT ---\n")
    logging.info("--- AGENT CYCLE ---")
    
    # Emit execution context
    context_env = create_request("execution.context_captured", {
        "context_id": f"ctx_{int(time.time())}",
        "session_id": "default",
        "task_id": "agent_loop",
        "model_id": "llama-default",
        "temperature": 0.7,
        "max_tokens": 512,
        "prompt_template_version": "v1",
        "tool_registry_version": "v1",
        "planner_version": "v1",
        "routing_decision": "general",
        "retrieved_memory_ids": [] # Can populate properly in Phase 4
    }, f"ctx_{int(time.time())}")
    s.sendall((json.dumps(context_env) + "\n").encode('utf-8'))
    
    llm_response = llm_client.generate(prompt, max_tokens=512)
    logging.info(f"Assistant: {llm_response}")
    
    messages.append({"role": "assistant", "content": llm_response})
    
    try:
        parsed_tool, error_reason = extract_tool_call(llm_response, registry)
        
        # Check for textual response indicating conversational reply
        clean_text = extract_text_response(llm_response)
        
        if clean_text:
            res = create_request("ui.output", {"text": clean_text}, f"ui_{int(time.time())}")
            s.sendall((json.dumps(res) + "\n").encode('utf-8'))

        if parsed_tool:
            args_str = json.dumps(parsed_tool['args'])
            status_text = f"[Executing: {parsed_tool['name']} {args_str}]"
            
            status_msg = create_request("ui.output", {"text": status_text}, f"st_{int(time.time())}")
            s.sendall((json.dumps(status_msg) + "\n").encode('utf-8'))
            
            req = create_request("tool.requested", {
                "task_id": "agent_loop",
                "tool_name": parsed_tool["name"],
                "args": parsed_tool["args"]
            }, f"req_{int(time.time())}")
            s.sendall((json.dumps(req) + "\n").encode('utf-8'))
            
        elif error_reason and "No JSON blocks found" not in error_reason:
            # Emit tool.rejected for invalid tool attempts
            logging.warning(f"Tool rejected: {error_reason}")
            rej = create_request("tool.rejected", {
                "task_id": "agent_loop",
                "tool_name": "unknown",
                "reason": error_reason
            }, f"rej_{int(time.time())}")
            s.sendall((json.dumps(rej) + "\n").encode('utf-8'))
            
            # Feed the rejection back to the LLM immediately to attempt a replan
            messages.append({"role": "system", "content": f"Tool call failed validation: {error_reason}"})
            if len(messages) > 20: messages = messages[-20:]
            run_agent_cycle(s, messages, embedder, index, llm_client)

    except Exception as e:
        logging.error(f"Cycle Error: {e}")

def main():
    logging.info("Astra Orchestrator initialized.")
    
    docs = parse_vault(VAULT_PATH)
    
    memory_config = config.get("memory", {})
    embedder_type = memory_config.get("embedder_type", "sentence-transformers")
    embedder_model = memory_config.get("embedder_model", "all-MiniLM-L6-v2")
    embedder_dim = memory_config.get("embedder_dim", 384 if embedder_type == "sentence-transformers" else 128)
    
    if embedder_type == "dummy":
        embedder = DummyEmbedder(dim=embedder_dim)
    else:
        embedder = RealEmbedder(model_name=embedder_model)
        
    index = MemoryIndex(dim=embedder.dim)
    if docs:
        texts = [d["text"] for d in docs]
        index.add(embedder.embed_batch(texts), docs)
        
    llm_client = route_task("general")
    
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
                    event = json.loads(line)
                    
                    if event.get("event") == "ui.input":
                        user_text = event["data"]["text"]
                        messages.append({"role": "user", "content": user_text})
                        # Prune history if too long (keep last 20)
                        if len(messages) > 20: messages = messages[-20:]
                        run_agent_cycle(s, messages, embedder, index, llm_client)
                        
                    elif event.get("event") == "tool.completed":
                        res_data = event["data"]["result"]
                        summary = json.dumps(res_data)
                        if len(summary) > 500: summary = summary[:500] + "... [truncated]"
                        
                        messages.append({"role": "system", "content": f"Tool result: {summary}"})
                        if len(messages) > 20: messages = messages[-20:]
                        run_agent_cycle(s, messages, embedder, index, llm_client)

                    elif event.get("event") == "tool.failed":
                        err = event["data"]["error"]
                        messages.append({"role": "system", "content": f"Tool failed: {err}"})
                        if len(messages) > 20: messages = messages[-20:]
                        run_agent_cycle(s, messages, embedder, index, llm_client)

        except Exception as e:
            logging.error(f"Runtime Error: {e}")

if __name__ == "__main__":
    main()
