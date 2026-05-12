import requests
import json

class LlamaClient:
    def __init__(self, server_url="http://localhost:8080/v1"):
        self.server_url = server_url
        
    def generate(self, prompt, max_tokens=512, temperature=0.7):
        try:
            response = requests.post(
                f"{self.server_url}/completions",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
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
    """
    Returns a LlamaClient wrapper that enforces task-specific generation parameters.
    """
    client = LlamaClient()
    
    if task_type == "classification":
        # Low temperature for deterministic classification
        client.default_params = {"max_tokens": 128, "temperature": 0.1}
    elif task_type == "reasoning":
        # Balanced for agent thoughts
        client.default_params = {"max_tokens": 512, "temperature": 0.7}
    elif task_type == "deep":
        # Higher creativity/exploration for complex plans
        client.default_params = {"max_tokens": 1024, "temperature": 0.8}
    else:
        client.default_params = {"max_tokens": 512, "temperature": 0.7}
        
    # Wrap generate to use defaults
    original_generate = client.generate
    def wrapped_generate(prompt, **kwargs):
        params = client.default_params.copy()
        params.update(kwargs)
        return original_generate(prompt, **params)
    
    client.generate = wrapped_generate
    return client
