use crate::events::EventEnvelope;
use crate::state::{SystemState, Task};

pub fn reduce(mut state: SystemState, event: &EventEnvelope) -> SystemState {
    match &event.data {
        crate::events::EventPayload::TaskCreated { task_id, goal } => {
            let task = Task {
                id: task_id.clone(),
                goal: goal.clone(),
                status: "planning".to_string(),
                ..Default::default()
            };
            state.tasks.insert(task_id.clone(), task);
            state.active_goal = Some(goal.clone());
            state.status = "planning".to_string();
        }
        crate::events::EventPayload::UserInput { text, .. } => {
            state.status = "capturing".to_string();
            state.active_goal = Some(text.clone());
        }
        crate::events::EventPayload::ExecutionContextCaptured { task_id, .. } => {
            if let Some(task) = state.tasks.get_mut(task_id) {
                task.status = "executing".to_string();
                state.status = "executing".to_string();
            }
        }
        crate::events::EventPayload::TaskCancelled { task_id } => {
            if let Some(task) = state.tasks.get_mut(task_id) {
                task.status = "cancelled".to_string();
                task.cancellation_flag = true;
            }
        }
        crate::events::EventPayload::IntentContracted { task_id, contract } => {
            if let Some(task) = state.tasks.get_mut(task_id) {
                let intent = crate::state::IntentContract {
                    objective: contract.objective.clone(),
                    constraints: contract.constraints.clone(),
                    requires_tools: contract.requires_tools,
                    requires_confirmation: contract.requires_confirmation,
                    persistence_policy: contract.persistence_policy.clone(),
                    expected_output_type: contract.expected_output_type.clone(),
                };
                task.intent = Some(intent);
            }
        }
        crate::events::EventPayload::ToolConfirmationRequired { task_id, tool_name, args, pending_id } => {
            let intent = state.tasks.get(task_id).and_then(|t| t.intent.clone());
            let pending = crate::state::PendingExecution {
                pending_id: pending_id.clone(),
                task_id: task_id.clone(),
                tool_name: tool_name.clone(),
                args: args.clone(),
                intent,
                status: "awaiting_confirmation".to_string(),
            };
            state.pending_executions.insert(pending_id.clone(), pending);
        }
        crate::events::EventPayload::ToolConfirmed { pending_id, .. } => {
            if let Some(pending) = state.pending_executions.get_mut(pending_id) {
                pending.status = "approved".to_string();
            }
        }
        crate::events::EventPayload::ToolDenied { pending_id, .. } => {
            if let Some(pending) = state.pending_executions.get_mut(pending_id) {
                pending.status = "denied".to_string();
            }
        }
        crate::events::EventPayload::ToolResult { task_id, .. } => {
            if let Some(task) = state.tasks.get_mut(task_id) {
                task.current_step = "tool_completed".to_string();
                // If this was the last step, the orchestrator should send TaskCompleted
            }
        }
        crate::events::EventPayload::TaskUpdated { task_id, status, .. } => {
            if let Some(task) = state.tasks.get_mut(task_id) {
                task.status = status.clone();
                state.status = status.clone();
            }
        }
        crate::events::EventPayload::TaskCompleted { task_id, .. } => {
            if let Some(task) = state.tasks.get_mut(task_id) {
                task.status = "completed".to_string();
                state.status = "idle".to_string();
                state.active_goal = None;
            }
        }
        crate::events::EventPayload::TaskFailed { task_id, retryable, .. } => {
            if let Some(task) = state.tasks.get_mut(task_id) {
                if *retryable && task.retry_count < task.max_retries {
                    task.status = "recovering".to_string();
                    state.status = "recovering".to_string();
                } else {
                    task.status = "failed".to_string();
                    state.status = "idle".to_string();
                    state.active_goal = None;
                }
            }
        }
        crate::events::EventPayload::TaskInterrupted { task_id, reason } => {
            if let Some(task) = state.tasks.get_mut(task_id) {
                task.status = "interrupted".to_string();
                task.interrupt_reason = Some(reason.clone());
                state.status = "interrupted".to_string();
            }
        }
        crate::events::EventPayload::MemoryRetrieved { task_id, .. } => {
            if let Some(task) = state.tasks.get_mut(task_id) {
                task.status = "planning".to_string();
                state.status = "planning".to_string();
            }
        }
        crate::events::EventPayload::MemoryWrite { .. } => {
            // Memory writes don't necessarily change task state immediately
        }
        crate::events::EventPayload::ContextUpdated { data } => {
            state.context_window = data.clone();
        }
        crate::events::EventPayload::SystemSuspend { .. } => {
            state.status = "suspended".to_string();
        }
        crate::events::EventPayload::SystemResume {} => {
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
    use crate::events::EventPayload;

    fn event(name: &str, data: EventPayload) -> EventEnvelope {
        EventEnvelope {
            schema_version: 1,
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
            &event("task.created", EventPayload::TaskCreated { task_id: "task-1".to_string(), goal: "rename files".to_string() }),
        );

        let task = state.tasks.get("task-1").expect("task should be created");
        assert_eq!(task.id, "task-1");
        assert_eq!(task.goal, "rename files");
        assert_eq!(task.status, "planning");
        assert!(!task.cancellation_flag);
        assert_eq!(state.status, "planning");
        assert_eq!(state.active_goal, Some("rename files".to_string()));
    }

    #[test]
    fn user_input_starts_capturing_state() {
        let state = reduce(SystemState::new(), &event("ui.input", EventPayload::UserInput { text: "hello".to_string(), context: json!({}), session_id: None }));
        assert_eq!(state.status, "capturing");
        assert_eq!(state.active_goal, Some("hello".to_string()));
    }

    #[test]
    fn execution_context_captured_starts_executing_state() {
        let state = reduce(
            SystemState::new(),
            &event("task.created", EventPayload::TaskCreated { task_id: "task-1".to_string(), goal: "work".to_string() }),
        );
        let state = reduce(state, &event("execution.context_captured", EventPayload::ExecutionContextCaptured { 
            context_id: "ctx".to_string(), session_id: "s".to_string(), task_id: "task-1".to_string(), 
            model_id: "m".to_string(), temperature: 0.7, max_tokens: 100, 
            prompt_template_version: "v1".to_string(), tool_registry_version: "v1".to_string(), 
            planner_version: "v1".to_string(), routing_decision: "r".to_string(), retrieved_memory_ids: vec![] 
        }));

        assert_eq!(state.tasks["task-1"].status, "executing");
        assert_eq!(state.status, "executing");
    }

    #[test]
    fn task_failed_with_retry_triggers_recovering() {
        let mut state = SystemState::new();
        state.tasks.insert("task-1".to_string(), Task {
            id: "task-1".to_string(),
            retry_count: 0,
            max_retries: 3,
            ..Default::default()
        });

        let state = reduce(state, &event("task.failed", EventPayload::TaskFailed { task_id: "task-1".to_string(), error: "fail".to_string(), retryable: true }));
        assert_eq!(state.tasks["task-1"].status, "recovering");
        assert_eq!(state.status, "recovering");
    }

    #[test]
    fn task_failed_without_retry_triggers_failed() {
        let state = reduce(
            SystemState::new(),
            &event("task.created", EventPayload::TaskCreated { task_id: "task-1".to_string(), goal: "work".to_string() }),
        );
        let state = reduce(state, &event("task.failed", EventPayload::TaskFailed { task_id: "task-1".to_string(), error: "fail".to_string(), retryable: false }));
        assert_eq!(state.tasks["task-1"].status, "failed");
        assert_eq!(state.status, "idle");
    }

    #[test]
    fn task_cancelled_marks_existing_task_cancelled() {
        let state = reduce(
            SystemState::new(),
            &event("task.created", EventPayload::TaskCreated { task_id: "task-1".to_string(), goal: "work".to_string() }),
        );
        let state = reduce(state, &event("task.cancelled", EventPayload::TaskCancelled { task_id: "task-1".to_string() }));

        let task = &state.tasks["task-1"];
        assert_eq!(task.status, "cancelled");
        assert!(task.cancellation_flag);
    }

    #[test]
    fn tool_completed_updates_current_step_for_existing_task() {
        let state = reduce(
            SystemState::new(),
            &event("task.created", EventPayload::TaskCreated { task_id: "task-1".to_string(), goal: "work".to_string() }),
        );
        let state = reduce(state, &event("tool.completed", EventPayload::ToolResult { task_id: "task-1".to_string(), tool_name: "test".to_string(), result: json!({}) }));

        assert_eq!(state.tasks["task-1"].current_step, "tool_completed");
    }

    #[test]
    fn context_updated_replaces_context_window() {
        let state = reduce(SystemState::new(), &event("context.updated", EventPayload::ContextUpdated { data: json!({"cwd": "/tmp"}) }));

        assert_eq!(state.context_window, json!({"cwd": "/tmp"}));
    }

    #[test]
    fn suspend_and_resume_update_system_status() {
        let state = reduce(SystemState::new(), &event("system.suspend", EventPayload::SystemSuspend { reason: "test".to_string() }));
        assert_eq!(state.status, "suspended");

        let state = reduce(state, &event("system.resume", EventPayload::SystemResume {}));
        assert_eq!(state.status, "idle");
    }
}
