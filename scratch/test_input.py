import socket
import json
import time

SOCKET_PATH = "/tmp/astra.sock"

def send_event(event, data):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(SOCKET_PATH)
        payload = {
            "jsonrpc": "2.0",
            "id": f"test_{int(time.time())}",
            "method": event,
            "params": data
        }
        s.sendall((json.dumps(payload) + "\n").encode('utf-8'))

if __name__ == "__main__":
    send_event("ui.input", {
        "type": "UserInput",
        "text": "hi",
        "context": {"active_app": "test_script"},
        "session_id": "test_session"
    })
    print("Sent hi to Astra")
