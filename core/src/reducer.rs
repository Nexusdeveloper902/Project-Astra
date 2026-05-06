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
        _ => {
            // Other events are ignored by the reducer for now
        }
    }
    state
}
