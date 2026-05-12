use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use serde_json::Value;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct IntentContract {
    pub objective: String,
    pub constraints: Vec<String>,
    pub task_type: String,
    pub requires_tools: bool,
    pub requires_confirmation: bool,
    pub persistence_policy: String,
    pub expected_output_type: String,
}

#[derive(Serialize, Deserialize, Debug, Clone, Default)]
pub struct Task {
    pub id: String,
    pub goal: String,
    pub intent: Option<IntentContract>,
    pub status: String, // capturing, classifying, retrieving, planning, executing, waiting_confirmation, recovering, completed, cancelled, interrupted, timed_out
    pub current_step: String,
    pub retry_count: u32,
    pub max_retries: u32,
    pub pending_actions: Vec<Value>,
    pub interrupt_reason: Option<String>,
    pub cancellation_flag: bool,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct PendingExecution {
    pub pending_id: String,
    pub task_id: String,
    pub tool_name: String,
    pub args: Value,
    pub intent: Option<IntentContract>,
    pub status: String,
}

#[derive(Serialize, Deserialize, Debug, Clone, Default)]
pub struct SystemState {
    pub tasks: HashMap<String, Task>,
    pub active_goal: Option<String>,
    pub pending_executions: HashMap<String, PendingExecution>,
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_state_starts_idle_with_empty_collections() {
        let state = SystemState::new();

        assert_eq!(state.status, "idle");
        assert!(state.tasks.is_empty());
        assert!(state.pending_executions.is_empty());
        assert!(state.active_goal.is_none());
        assert!(state.context_window.is_null());
    }

    #[test]
    fn default_task_has_no_pending_work_and_is_not_cancelled() {
        let task = Task::default();

        assert_eq!(task.retry_count, 0);
        assert!(task.pending_actions.is_empty());
        assert!(!task.cancellation_flag);
        assert_eq!(task.status, "");
    }
}
