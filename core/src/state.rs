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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_state_starts_idle_with_empty_collections() {
        let state = SystemState::new();

        assert_eq!(state.status, "idle");
        assert!(state.tasks.is_empty());
        assert!(state.pending_tools.is_empty());
        assert!(state.active_goal.is_none());
        assert!(state.context_window.is_null());
    }

    #[test]
    fn default_task_has_no_pending_work_and_is_not_cancelled() {
        let task = Task::default();

        assert_eq!(task.retries, 0);
        assert!(task.pending_actions.is_empty());
        assert!(!task.cancellation_flag);
        assert_eq!(task.status, "");
    }
}
