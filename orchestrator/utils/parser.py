import json
import logging

def extract_tool_call(text, registry):
    """
    Extracts a tool call, prioritizing blocks between TOOL_CALL_START and TOOL_CALL_END.
    Falls back to searching for raw JSON blocks.
    Returns:
        (dict, str) - (parsed_tool, error_reason)
    """
    import re
    
    # Try explicit delimiters first
    delimited_match = re.search(r'TOOL_CALL_START(.*?)TOOL_CALL_END', text, re.DOTALL)
    if delimited_match:
        block = delimited_match.group(1).strip()
        parsed, err = _parse_and_validate(block, registry)
        if parsed:
            return parsed, None
        else:
            return None, f"Delimited tool call failed: {err}"

    # Fallback to finding all potential json blocks by finding matching braces
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
        parsed, err = _parse_and_validate(block, registry)
        if parsed:
            return parsed, None
            
    return None, "Found JSON blocks but none contained a valid tool call"

def _parse_and_validate(block, registry):
    try:
        # Sanitize invalid escape sequences common in LLM bash commands
        sanitized = block.replace(r'\(', r'\\(').replace(r'\*', r'\\*').replace(r'\)', r'\\)')
        parsed = json.loads(sanitized)
        
        if not isinstance(parsed, dict):
            return None, "Not a dictionary"
            
        if "tool_name" not in parsed or "args" not in parsed:
            return None, "Missing tool_name or args"
            
        tool_name = parsed["tool_name"]
        args = parsed["args"]
        
        tool_names = [t["name"] for t in registry.get_all_tools()]
        if tool_name not in tool_names:
            return None, f"Tool '{tool_name}' is not in the registry"
            
        return {"name": tool_name, "args": args}, None
        
    except json.JSONDecodeError as e:
        return None, str(e)

def extract_text_response(text):
    """
    Returns the conversational part of the response, removing tool calls.
    """
    import re
    # Remove delimited blocks
    clean = re.sub(r'TOOL_CALL_START.*?TOOL_CALL_END', '', text, flags=re.DOTALL)
    # Remove raw JSON blocks (fallback)
    clean = re.sub(r'\{.*\}', '', clean, flags=re.DOTALL).strip()
    
    clean_text = "\n".join([line for line in clean.splitlines() if not line.strip().startswith(">")])
    return clean_text.strip()
