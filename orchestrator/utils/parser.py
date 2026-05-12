import json
import logging

def extract_tool_call(text, registry):
    """
    Extracts the last JSON block containing 'tool_name' and 'args',
    and validates it against the registry.
    Returns:
        (dict, str) - (parsed_tool, error_reason)
    """
    # Find all potential json blocks by finding matching braces
    blocks = []
    depth = 0
    start = -1
    for i, char in enumerate(text):
        if char == '{':
            if depth == 0:
                start = i
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0 and start != -1:
                blocks.append(text[start:i+1])
            elif depth < 0:
                depth = 0 # Ignore unmatched closing braces
                
    if not blocks:
        return None, "No JSON blocks found in response"

    # Evaluate blocks from last to first
    for block in reversed(blocks):
        try:
            # Sanitize invalid escape sequences common in LLM bash commands
            sanitized = block.replace(r'\(', r'\\(').replace(r'\*', r'\\*').replace(r'\)', r'\\)')
            parsed = json.loads(sanitized)
            
            if not isinstance(parsed, dict):
                continue
                
            if "tool_name" not in parsed or "args" not in parsed:
                continue
                
            tool_name = parsed["tool_name"]
            args = parsed["args"]
            
            if tool_name not in registry.get_all_tools():
                # Extracting names from tool schemas
                tool_names = [t["name"] for t in registry.get_all_tools()]
                if tool_name not in tool_names:
                    return None, f"Tool '{tool_name}' is not in the registry"
                
            # Valid tool call found
            return {"name": tool_name, "args": args}, None
            
        except json.JSONDecodeError as e:
            logging.debug(f"Failed to parse JSON block: {e}")
            continue
            
    return None, "Found JSON blocks but none contained a valid tool call"

def extract_text_response(text):
    """
    Returns the conversational part of the response, removing tool calls.
    """
    import re
    text_response = re.sub(r'\{.*\}', '', text, flags=re.DOTALL).strip()
    clean_text = "\n".join([line for line in text_response.splitlines() if not line.strip().startswith(">")])
    return clean_text
