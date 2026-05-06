use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use serde_json::Value;

#[derive(Serialize, Deserialize, Debug, Clone, Default)]
pub struct Task {
    pub id: String,
    pub goal: String,
    pub status: String,
    pub current_step: String,
    pub retries: u32,
    pub pending_actions: Vec<Value>,
    pub cancellation_flag: bool,
}

#[derive(Serialize, Deserialize, Debug, Clone, Default)]
pub struct SystemState {
    pub tasks: HashMap<String, Task>,
    pub active_goal: Option<String>,
    pub pending_tools: Vec<Value>,
    pub context_window: Value,
    pub status: String, // idle, planning, executing, etc.
}

impl SystemState {
    pub fn new() -> Self {
        SystemState {
            status: "idle".to_string(),
            ..Default::default()
        }
    }
}
