use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct EventEnvelope {
    #[serde(default = "default_schema_version")]
    pub schema_version: u32,
    pub event: String,
    pub timestamp: u64,
    pub source: String,
    pub data: EventPayload,
}

fn default_schema_version() -> u32 {
    1
}

#[derive(Serialize, Deserialize, Debug, Clone)]
#[serde(tag = "type")]
pub enum EventPayload {
    TaskCreated { task_id: String, goal: String },
    TaskCancelled { task_id: String },
    UserInput { text: String, context: Value, session_id: Option<String> },
    ToolRequest { task_id: String, tool_name: String, args: Value, danger_tier: Option<String> },
    ToolResult { task_id: String, tool_name: String, result: Value },
    ToolRejected { task_id: String, tool_name: String, reason: String },
    ToolConfirmationRequired { task_id: String, tool_name: String, args: Value, pending_id: String },
    ToolConfirmed { task_id: String, tool_name: String, pending_id: String },
    ToolDenied { task_id: String, tool_name: String, pending_id: String, reason: String },
    IntentContracted { task_id: String, contract: IntentContractPayload },
    ExecutionContextCaptured { 
        context_id: String, session_id: String, task_id: String, model_id: String, 
        temperature: f32, max_tokens: u32, prompt_template_version: String, 
        tool_registry_version: String, planner_version: String, routing_decision: String, 
        retrieved_memory_ids: Vec<String> 
    },
    UiOutput { text: String },
    ContextUpdated { data: Value },
    TaskUpdated { task_id: String, status: String, progress: Option<f32> },
    TaskCompleted { task_id: String, result: Value },
    TaskFailed { task_id: String, error: String, retryable: bool },
    TaskInterrupted { task_id: String, reason: String },
    MemoryRetrieved { task_id: String, memories: Vec<Value> },
    MemoryWrite { task_id: String, content: String },
    SystemSuspend { reason: String },
    SystemResume {},
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct IntentContractPayload {
    pub objective: String,
    pub constraints: Vec<String>,
    pub requires_tools: bool,
    pub requires_confirmation: bool,
    pub persistence_policy: String,
    pub expected_output_type: String,
}
