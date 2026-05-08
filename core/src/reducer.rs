use crate::events::EventEnvelope;
use crate::state::{SystemState, Task};

pub fn reduce(mut state: SystemState, event: &EventEnvelope) -> SystemState {
    match event.event.as_str() {
        "task.created" => {
            if let Some(task_id) = event.data.get("task_id").and_then(|v| v.as_str()) {
                let goal = event.data.get("goal").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let task = Task {
                    id: task_id.to_string(),
                    goal,
                    status: "running".to_string(),
                    ..Default::default()
                };
                state.tasks.insert(task_id.to_string(), task);
            }
        }
        "task.cancelled" => {
            if let Some(task_id) = event.data.get("task_id").and_then(|v| v.as_str()) {
                if let Some(task) = state.tasks.get_mut(task_id) {
                    task.status = "cancelled".to_string();
                    task.cancellation_flag = true;
                }
            }
        }
        "tool.completed" => {
             if let Some(task_id) = event.data.get("task_id").and_then(|v| v.as_str()) {
                 if let Some(task) = state.tasks.get_mut(task_id) {
                     task.current_step = "tool_completed".to_string();
                 }
             }
        }
        "context.updated" => {
             state.context_window = event.data.clone();
        }
        "system.suspend" => {
            state.status = "suspended".to_string();
        }
        "system.resume" => {
            state.status = "idle".to_string();
        }
        _ => {
            // Other events are ignored by the reducer for now
        }
    }
    state
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn event(name: &str, data: serde_json::Value) -> EventEnvelope {
        EventEnvelope {
            event: name.to_string(),
            timestamp: 123,
            source: "test".to_string(),
            data,
        }
    }

    #[test]
    fn task_created_adds_running_task_with_goal() {
        let state = reduce(
            SystemState::new(),
            &event("task.created", json!({"task_id": "task-1", "goal": "rename files"})),
        );

        let task = state.tasks.get("task-1").expect("task should be created");
        assert_eq!(task.id, "task-1");
        assert_eq!(task.goal, "rename files");
        assert_eq!(task.status, "running");
        assert!(!task.cancellation_flag);
    }

    #[test]
    fn task_created_uses_empty_goal_when_goal_is_missing() {
        let state = reduce(
            SystemState::new(),
            &event("task.created", json!({"task_id": "task-1"})),
        );

        assert_eq!(state.tasks["task-1"].goal, "");
    }

    #[test]
    fn task_created_ignores_events_without_task_id() {
        let state = reduce(SystemState::new(), &event("task.created", json!({"goal": "missing id"})));

        assert!(state.tasks.is_empty());
    }

    #[test]
    fn task_cancelled_marks_existing_task_cancelled() {
        let state = reduce(
            SystemState::new(),
            &event("task.created", json!({"task_id": "task-1", "goal": "work"})),
        );
        let state = reduce(state, &event("task.cancelled", json!({"task_id": "task-1"})));

        let task = &state.tasks["task-1"];
        assert_eq!(task.status, "cancelled");
        assert!(task.cancellation_flag);
    }

    #[test]
    fn task_cancelled_ignores_unknown_task() {
        let state = reduce(SystemState::new(), &event("task.cancelled", json!({"task_id": "missing"})));

        assert!(state.tasks.is_empty());
    }

    #[test]
    fn tool_completed_updates_current_step_for_existing_task() {
        let state = reduce(
            SystemState::new(),
            &event("task.created", json!({"task_id": "task-1", "goal": "work"})),
        );
        let state = reduce(state, &event("tool.completed", json!({"task_id": "task-1"})));

        assert_eq!(state.tasks["task-1"].current_step, "tool_completed");
    }

    #[test]
    fn context_updated_replaces_context_window() {
        let state = reduce(SystemState::new(), &event("context.updated", json!({"cwd": "/tmp"})));

        assert_eq!(state.context_window, json!({"cwd": "/tmp"}));
    }

    #[test]
    fn suspend_and_resume_update_system_status() {
        let state = reduce(SystemState::new(), &event("system.suspend", json!({})));
        assert_eq!(state.status, "suspended");

        let state = reduce(state, &event("system.resume", json!({})));
        assert_eq!(state.status, "idle");
    }

    #[test]
    fn unknown_events_leave_state_unchanged() {
        let mut state = SystemState::new();
        state.status = "planning".to_string();

        let next = reduce(state, &event("unknown.event", json!({"ignored": true})));

        assert_eq!(next.status, "planning");
        assert!(next.tasks.is_empty());
    }
}
