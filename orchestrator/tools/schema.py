class ToolSchema:
    def __init__(self, name, description, input_schema, output_schema, danger_tier="low"):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.danger_tier = danger_tier

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "danger_tier": self.danger_tier
        }

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, tool: ToolSchema):
        self.tools[tool.name] = tool

    def get_all_tools(self):
        return [t.to_dict() for t in self.tools.values()]

# Register base tools
registry = ToolRegistry()
registry.register(ToolSchema(
    name="run_shell",
    description="Run a shell command",
    input_schema={"cmd": "string"},
    output_schema={"stdout": "string", "stderr": "string"},
    danger_tier="medium"
))

registry.register(ToolSchema(
    name="save_memory",
    description="Save a new memory or observation about the user to the structured vault. Categorize it (preferences, procedures, facts, logs) and add relevant tags.",
    input_schema={
        "content": "string (the observation or fact)",
        "category": "string (one of: preferences, procedures, facts, logs)",
        "tags": "array of strings",
        "confidence": "number (0.0 to 1.0)"
    },
    output_schema={"status": "string", "path": "string"},
    danger_tier="low"
))
