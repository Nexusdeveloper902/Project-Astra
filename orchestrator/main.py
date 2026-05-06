import json
import socket
import sys
import os
import time
import re

print("--- ASTRA STARTUP FINGERPRINT: 2026-05-06-15:38 ---")

from llm.prompt import construct_prompt
from llm.client import route_task
from tools.schema import registry
from memory.parser import parse_vault
from memory.embedder import DummyEmbedder
from memory.index import MemoryIndex

SOCKET_PATH = "/tmp/astra.sock"
VAULT_PATH = "/home/jperez/Astra/memories"

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
    
    print("\n--- AGENT PROMPT ---")
    print(prompt)
    print("--- END PROMPT ---\n")
    
    print("\n--- AGENT CYCLE ---")
    llm_response = llm_client.generate(prompt, max_tokens=512)
    print(f"Assistant: {llm_response}")
    
    messages.append({"role": "assistant", "content": llm_response})
    
    try:
        parsed_tool = None
        json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(0)
                parsed_json = json.loads(json_str)
                if "tool_name" in parsed_json and "args" in parsed_json:
                    parsed_tool = {"name": parsed_json["tool_name"], "args": parsed_json["args"]}
            except: pass

        text_response = re.sub(r'\{.*\}', '', llm_response, flags=re.DOTALL).strip()
        clean_text = "\n".join([line for line in text_response.splitlines() if not line.strip().startswith(">")])
        
        if clean_text:
            res = create_request("ui.output", {"text": clean_text}, f"ui_{int(time.time())}")
            s.sendall((json.dumps(res) + "\n").encode('utf-8'))

        if parsed_tool:
            status_msg = create_request("ui.output", {"text": f"[Action: {parsed_tool['name']}]"}, f"st_{int(time.time())}")
            s.sendall((json.dumps(status_msg) + "\n").encode('utf-8'))
            
            req = create_request("tool.requested", {
                "task_id": "agent_loop",
                "tool_name": parsed_tool["name"],
                "args": parsed_tool["args"]
            }, f"req_{int(time.time())}")
            s.sendall((json.dumps(req) + "\n").encode('utf-8'))
            
    except Exception as e:
        print(f"Cycle Error: {e}")

def main():
    print("Astra Orchestrator initialized.")
    
    docs = parse_vault(VAULT_PATH)
    embedder = DummyEmbedder(dim=128)
    index = MemoryIndex(dim=128)
    if docs:
        texts = [d["text"] for d in docs]
        index.add(embedder.embed_batch(texts), docs)
        
    llm_client = route_task("general")
    
    print(f"Connecting to {SOCKET_PATH}...")
    for _ in range(20):
        if os.path.exists(SOCKET_PATH): break
        time.sleep(0.5)
    else:
        sys.exit(1)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        try:
            s.connect(SOCKET_PATH)
            print("Connected. Ready for Agentic Loops.")
            
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
                    event = json.loads(line)
                    
                    if event.get("event") == "ui.input":
                        user_text = event["data"]["text"]
                        messages.append({"role": "user", "content": user_text})
                        run_agent_cycle(s, messages, embedder, index, llm_client)
                        
                    elif event.get("event") == "tool.completed":
                        res_data = event["data"]["result"]
                        summary = json.dumps(res_data)
                        if len(summary) > 500: summary = summary[:500] + "... [truncated]"
                        
                        messages.append({"role": "system", "content": f"Tool result: {summary}"})
                        run_agent_cycle(s, messages, embedder, index, llm_client)

                    elif event.get("event") == "tool.failed":
                        err = event["data"]["error"]
                        messages.append({"role": "system", "content": f"Tool failed: {err}"})
                        run_agent_cycle(s, messages, embedder, index, llm_client)

        except Exception as e:
            print(f"Runtime Error: {e}")

if __name__ == "__main__":
    main()
