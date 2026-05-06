import json

SYSTEM_CORE_INSTRUCTION = """<|im_start|>system
You are Astra, a local-first intelligent assistant.
Your goal is to assist the user by using tools, retrieving memories, and reasoning through tasks.

Always respond in JSON when returning a tool call. Use this exact schema:
{
  "tool_name": "name of the tool",
  "args": {
    "arg1": "value"
  }
}
If you do not want to use a tool, output your response as plain conversational text without JSON.

GUIDELINES:
1. MANDATORY: You must ask for explicit user confirmation (e.g., "Shall I proceed with [action]?") BEFORE executing any system-modifying tool (run_shell with rm, mkdir, mv, etc.). 
2. Never execute a modification tool in the same turn you propose it. Propose the action first, wait for user "Yes", then execute.
3. Always ask for clarification if a name or path is not explicitly provided.
4. When checking if a directory exists, use `ls -d` to avoid empty output from empty folders.
5. Prioritize searching in visible home directories. Avoid system caches like `.cache` or `.local`.
6. Be concise and professional. Do not use emojis.
<|im_end|>"""

def construct_prompt(messages, active_context, memory_retrievals, tools, task_state):
    # Start with the core system instruction
    prompt = [SYSTEM_CORE_INSTRUCTION]
    
    # Inject Tools and Context as a system-level update
    context_info = f"""
<|im_start|>system
[Available Tools]
{json.dumps(tools, indent=2)}

[System Context]
{json.dumps(active_context)}
Memory Snippets: {", ".join(memory_retrievals)}
Task State: {json.dumps(task_state)}
<|im_end|>"""
    prompt.append(context_info)
    
    # Append the conversation history
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        prompt.append(f"<|im_start|>{role}\n{content}<|im_end|>")
    
    # Add final assistant trigger
    prompt.append("<|im_start|>assistant")
    
    return "\n".join(prompt)
