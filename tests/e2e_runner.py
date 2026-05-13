import socket
import json
import time
import unittest

class AstraE2ETestCase(unittest.TestCase):
    SOCKET_PATH = "/tmp/astra.sock"

    def setUp(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.SOCKET_PATH)
        self.sock.settimeout(60.0) # 1 minute timeout for LLM inference
        self.events = []
        self.buffer = ""

    def tearDown(self):
        self.sock.close()

    def send_prompt(self, text):
        req_id = f"test_{int(time.time())}"
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "ui.input",
            "params": {
                "text": text,
                "context": {"active_app": "Astra Test Runner"}
            }
        }
        self.sock.sendall((json.dumps(req) + "\n").encode('utf-8'))

    def wait_for_response(self, auto_reply_yes=False):
        final_text = ""
        self.sock.settimeout(15.0) # Wait 15 seconds for the agent to idle
        
        while True:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                
                self.buffer += data.decode('utf-8')
                lines = self.buffer.split('\n')
                self.buffer = lines.pop()
                
                for line in lines:
                    if not line.strip(): continue
                    event = json.loads(line)
                    if "event" not in event:
                        continue
                    self.events.append(event)
                    
                    if event.get("event") == "ui.output":
                        text = event.get("data", {}).get("text", "")
                        # Ignore tool execution status outputs
                        if not text.startswith("[Executing:"):
                            final_text = text
                            if auto_reply_yes and "?" in text and "proceed" in text.lower():
                                # Assistant is asking for confirmation to proceed, auto-reply "yes"
                                self.send_prompt("yes")
                                self.sock.settimeout(15.0)
            except socket.timeout:
                # If we timeout and we have a final_text, it means the agent finished its loop
                if final_text:
                    return final_text
                self.fail("Timed out waiting for Astra response.")

    def get_all_events(self):
        return self.events

    def wait_for_event(self, event_type, timeout=10.0):
        """Wait until an event of a specific type is received."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self.sock.settimeout(1.0)
                data = self.sock.recv(4096)
                if data:
                    self.buffer += data.decode('utf-8')
                    lines = self.buffer.split('\n')
                    self.buffer = lines.pop()
                    for line in lines:
                        if not line.strip(): continue
                        event = json.loads(line)
                        if "event" not in event:
                            continue
                        self.events.append(event)
                        if event.get("event") == event_type:
                            return [e for e in self.events if e.get("event") == event_type]
            except socket.timeout:
                continue
        return [e for e in self.events if e.get("event") == event_type]

    def get_requested_tools(self):
        return [e for e in self.events if e.get("event") == "tool.requested"]

    def assertToolCalled(self, tool_name, args_substring=None):
        tools = self.get_requested_tools()
        for t in tools:
            if t["data"]["tool_name"] == tool_name:
                if args_substring:
                    args_str = json.dumps(t["data"]["args"])
                    if args_substring in args_str:
                        return True
                else:
                    return True
        
        args_str = f" with args containing '{args_substring}'" if args_substring else ""
        self.fail(f"Tool '{tool_name}'{args_str} was not called. Tools called: {[t['data']['tool_name'] for t in tools]}")
