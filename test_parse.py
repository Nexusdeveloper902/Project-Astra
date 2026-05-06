import re, json

llm_response = """
build      : b8999-b97ebdc98
model      : qwen2.5-14b-instruct-q6_k-00001-of-00004.gguf
modalities : text

available commands:
  /exit or Ctrl+C     stop or exit

> You are Astra, a local-first intelligent assistant.
Your goal is to assist the user by using tools, retrieving memories, and reasoning through tasks.
Always respond in JSON when returning a tool call. Use this exact schema:
{
  "tool_name": "name of the tool",
  "args": {
    "arg1": "value"
  }
}

[Available Tools]
{
  "name": "run_shell"
}

Hello! How can I assist you today?

[ Prompt: 450.6 t/s | Generation: 24.8 t/s ]

> 
"""

json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
print(f"json_match: {json_match is not None}")

text_only = re.sub(r'\{.*\}', '', llm_response, flags=re.DOTALL) if json_match else llm_response
clean_text = "\n".join([line for line in text_only.splitlines() if not line.strip().startswith(">")])

print("CLEAN TEXT:")
print(clean_text)
print("FIRST 200:")
print(clean_text.strip()[:200])

