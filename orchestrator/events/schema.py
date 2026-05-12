from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

class IntentContractPayload(BaseModel):
    objective: str
    constraints: List[str]
    requires_tools: bool
    requires_confirmation: bool
    persistence_policy: str
    expected_output_type: str

class TaskCreatedPayload(BaseModel):
    type: Literal["TaskCreated"] = "TaskCreated"
    task_id: str
    goal: str

class TaskCancelledPayload(BaseModel):
    type: Literal["TaskCancelled"] = "TaskCancelled"
    task_id: str

class UserInputPayload(BaseModel):
    type: Literal["UserInput"] = "UserInput"
    text: str
    context: Dict[str, Any]
    session_id: Optional[str] = None

class ToolRequestPayload(BaseModel):
    type: Literal["ToolRequest"] = "ToolRequest"
    task_id: str
    tool_name: str
    args: Dict[str, Any]
    danger_tier: Optional[str] = None

class ToolResultPayload(BaseModel):
    type: Literal["ToolResult"] = "ToolResult"
    task_id: str
    tool_name: str
    result: Any

class ToolRejectedPayload(BaseModel):
    type: Literal["ToolRejected"] = "ToolRejected"
    task_id: str
    tool_name: str
    reason: str

class ToolConfirmationRequiredPayload(BaseModel):
    type: Literal["ToolConfirmationRequired"] = "ToolConfirmationRequired"
    task_id: str
    tool_name: str
    args: Dict[str, Any]
    pending_id: str

class ToolConfirmedPayload(BaseModel):
    type: Literal["ToolConfirmed"] = "ToolConfirmed"
    task_id: str
    tool_name: str
    pending_id: str

class ToolDeniedPayload(BaseModel):
    type: Literal["ToolDenied"] = "ToolDenied"
    task_id: str
    tool_name: str
    pending_id: str
    reason: str

class IntentContractedPayload(BaseModel):
    type: Literal["IntentContracted"] = "IntentContracted"
    task_id: str
    contract: IntentContractPayload

class ExecutionContextCapturedPayload(BaseModel):
    type: Literal["ExecutionContextCaptured"] = "ExecutionContextCaptured"
    context_id: str
    session_id: str
    task_id: str
    model_id: str
    temperature: float
    max_tokens: int
    prompt_template_version: str
    tool_registry_version: str
    planner_version: str
    routing_decision: str
    retrieved_memory_ids: List[str]

class UiOutputPayload(BaseModel):
    type: Literal["UiOutput"] = "UiOutput"
    text: str

class ContextUpdatedPayload(BaseModel):
    type: Literal["ContextUpdated"] = "ContextUpdated"
    data: Dict[str, Any]

class SystemSuspendPayload(BaseModel):
    type: Literal["SystemSuspend"] = "SystemSuspend"
    reason: str

class SystemResumePayload(BaseModel):
    type: Literal["SystemResume"] = "SystemResume"

EventPayload = Union[
    TaskCreatedPayload,
    TaskCancelledPayload,
    UserInputPayload,
    ToolRequestPayload,
    ToolResultPayload,
    ToolRejectedPayload,
    ToolConfirmationRequiredPayload,
    ToolConfirmedPayload,
    ToolDeniedPayload,
    IntentContractedPayload,
    ExecutionContextCapturedPayload,
    UiOutputPayload,
    ContextUpdatedPayload,
    SystemSuspendPayload,
    SystemResumePayload
]

class EventEnvelope(BaseModel):
    schema_version: int = 1
    event: str
    timestamp: int
    source: str
    data: EventPayload
