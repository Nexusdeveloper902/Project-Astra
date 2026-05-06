import requests
import json

class LlamaClient:
    def __init__(self, server_url="http://localhost:8080/v1"):
        self.server_url = server_url
        
    def generate(self, prompt, max_tokens=512):
        try:
            response = requests.post(
                f"{self.server_url}/completions",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "stop": ["<|im_end|>", "<|endoftext|>"]
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["text"].strip()
        except Exception as e:
            print(f"LLM Error: {e}")
            return "Error calling LLM."

def route_task(task_type):
    print(f"Routing task '{task_type}' to Medium model (HTTP Server).")
    return LlamaClient()
