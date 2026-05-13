import logging

def should_store(content: str, category: str, intent_contract: dict) -> bool:
    """
    Decides if a memory should be persisted based on the intent contract and heuristics.
    """
    policy = intent_contract.get("persistence_policy", "if_useful")
    
    if policy == "never":
        logging.info(f"Memory Policy: Skipping storage (policy=never)")
        return False
    
    if policy == "always":
        return True
    
    # Heuristics for 'if_useful'
    content_lower = content.lower()
    
    # 1. Prefer stable categories (exempt from length check)
    stable_categories = ["preferences", "procedures", "facts"]
    if category in stable_categories:
        return True
    
    # 2. Ignore obvious UI/system state chatter that doesn't add long-term value
    transient_keywords = ["clicked", "hovered", "scrolled", "window resized", "status: ready"]
    if any(k in content_lower for k in transient_keywords):
        logging.info(f"Memory Policy: Ignoring transient system chatter")
        return False
    
    # 3. Ignore very short or transient chatter for other categories
    if len(content) < 20:
        logging.info(f"Memory Policy: Ignoring short content ('{content[:20]}...')")
        return False
        
    # 4. If it's a 'log', we only save if it looks like a significant summary
    if category == "logs" and len(content) < 100:
        logging.info(f"Memory Policy: Ignoring short log entry")
        return False

    return True

def summarize_task_for_memory(task_goal: str, result: str) -> str:
    """
    Creates a concise summary of a completed task for long-term storage.
    """
    return f"Completed Task: {task_goal}\nResult: {result}"
