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
1. SEARCH WITHOUT PERMISSION: Never ask for permission to use `ls`, `find`, `cat`, or `grep`. Just execute these tools immediately to gather information.
2. HIDDEN FILE BLACKLIST: Do NOT search or list hidden files/folders (anything starting with a `.`) unless the user explicitly requests hidden files. Ignore `.git`, `.cache`, `.local`, etc.
3. MANDATORY CONFIRMATION: You MUST get explicit user confirmation BEFORE executing any system-modifying tool (e.g., `rm`, `mkdir`, `mv`, `write_file`).
4. BUNDLE REASONING: Find the target first, then present the result and ask: "I found [target]. Shall I proceed with [action]?"
5. SCOPE: Focus exclusively on the user's most recent request. Do not attempt to resume old tasks unless they are directly relevant.
6. PROFESSIONALISM: Be concise. No emojis.
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
