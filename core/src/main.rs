mod db;
mod events;
mod gamemode;
mod ipc;
mod reducer;
mod security;
mod state;
mod tools;
mod config;

use crossbeam_channel::{unbounded, Receiver, Sender};
use db::Db;
use events::EventEnvelope;
use ipc::{JsonRpcRequest, JsonRpcResponse};
use state::SystemState;
use std::fs;
use std::io::{Read, Write};
use std::os::unix::net::{UnixListener, UnixStream};
use std::process::Command;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

fn stop_heavy_components() {
    log::info!("[Core] Suspending heavy components for Game Mode...");
    let targets = [
        ("-f", "llama-server"),
        ("-f", "orchestrator/main.py"),
        ("-f", "astra-hud"),
        ("-x", "hud"),
        ("-f", "smart-wallpaper-daemon"),
        ("-f", "mpvpaper"),
        ("-f", "ComfyUI"),
    ];

    for signal in ["-TERM", "-KILL"] {
        for (match_mode, pattern) in targets {
            let _ = Command::new("pkill")
                .arg(signal)
                .arg(match_mode)
                .arg(pattern)
                .output();
        }
    }
}

fn is_shell_safe(cmd: &str) -> bool {
    let cmd = cmd.trim();
    let safe_tools = ["ls", "cat", "grep", "pwd", "find", "du", "df", "echo", "head", "tail", "which"];
    
    // Check if it starts with a safe tool
    let starts_with_safe = safe_tools.iter().any(|&tool| {
        cmd == tool || cmd.starts_with(&(tool.to_string() + " "))
    });

    if !starts_with_safe {
        return false;
    }

    // Block redirection and pipes to potentially dangerous tools
    let dangerous_tokens = [">", ">>", "|", ";", "&", "$(", "`", "rm", "mv", "cp", "mkdir", "chmod", "chown", "sudo", "apt", "dnf", "yum", "pip", "npm", "curl", "wget"];
    
    // Simple heuristic: if any dangerous token is present after the tool name
    // (We allow the tool name itself, which we already checked is safe)
    let parts: Vec<&str> = cmd.split_whitespace().collect();
    if parts.len() > 1 {
        for part in &parts[1..] {
            if dangerous_tokens.contains(part) {
                return false;
            }
            // Also check for sub-strings like ">"
            if part.contains('>') || part.contains('|') || part.contains(';') {
                return false;
            }
        }
    }

    true
}

fn start_heavy_components() {
    if matches!(gamemode::is_game_mode_enabled(), Some(true)) {
        log::info!("[Core] Game Mode is still active; skipping Astra resume.");
        return;
    }

    log::info!("[Core] Resuming Astra components...");
    let _ = Command::new("bash")
        .arg(&config::CONFIG.core.toggle_script_path)
        .spawn();
}

fn handle_client(mut stream: UnixStream, event_sender: Sender<EventEnvelope>) {
    let mut buffer = [0; 4096];
    let mut read_buffer = String::new();
    loop {
        match stream.read(&mut buffer) {
            Ok(size) => {
                if size == 0 {
                    break;
                }
                read_buffer.push_str(&String::from_utf8_lossy(&buffer[..size]));
                while let Some(newline_idx) = read_buffer.find('\n') {
                    let line: String = read_buffer.drain(..=newline_idx).collect();
                    let line = line.trim();
                    if line.trim().is_empty() {
                        continue;
                    }
                    match serde_json::from_str::<JsonRpcRequest>(line) {
                        Ok(req) => {
                            log::debug!("IPC: Received request {:?}", req.method);
                            if matches!(gamemode::is_game_mode_enabled(), Some(true)) {
                                let res = JsonRpcResponse::error(
                                    req.id,
                                    -32001,
                                    "Astra is suspended while Hyprland Game Mode is active",
                                );
                                let res_str = format!("{}\n", serde_json::to_string(&res).unwrap());
                                let _ = stream.write_all(res_str.as_bytes());
                                continue;
                            }

                            let mut params = req.params.clone();
                            if let serde_json::Value::Object(ref mut map) = params {
                                let event_type = match req.method.as_str() {
                                    "ui.input" => "UserInput",
                                    "task.created" => "TaskCreated",
                                    "task.updated" => "TaskUpdated",
                                    "task.completed" => "TaskCompleted",
                                    "task.failed" => "TaskFailed",
                                    "task.interrupted" => "TaskInterrupted",
                                    "memory.retrieved" => "MemoryRetrieved",
                                    "memory.write" => "MemoryWrite",
                                    "tool.requested" => "ToolRequest",
                                    "tool.completed" => "ToolResult",
                                    "tool.rejected" => "ToolRejected",
                                    "tool.confirmation_required" => "ToolConfirmationRequired",
                                    "tool.confirmed" => "ToolConfirmed",
                                    "tool.denied" => "ToolDenied",
                                    "intent.contracted" => "IntentContracted",
                                    "execution.context_captured" => "ExecutionContextCaptured",
                                    "ui.output" => "UiOutput",
                                    "context.updated" => "ContextUpdated",
                                    "system.suspend" => "SystemSuspend",
                                    "system.resume" => "SystemResume",
                                    _ => "Unknown",
                                };
                                map.insert("type".to_string(), serde_json::Value::String(event_type.to_string()));
                            }

                            match serde_json::from_value::<events::EventPayload>(params) {
                                Ok(data) => {
                                    let env = EventEnvelope {
                                        schema_version: 1,
                                        event: req.method.clone(),
                                        timestamp: now_secs(),
                                        source: "ipc".to_string(),
                                        data,
                                    };
                                    if let Err(e) = event_sender.send(env) {
                                        log::error!("Failed to send event to queue: {}", e);
                                    }
                                    let res = JsonRpcResponse::success(
                                        req.id,
                                        serde_json::json!({"status": "queued"}),
                                    );
                                    let res_str = format!("{}\n", serde_json::to_string(&res).unwrap());
                                    let _ = stream.write_all(res_str.as_bytes());
                                },
                                Err(e) => {
                                    log::error!("Schema validation failed for {}: {}", req.method, e);
                                    let res = JsonRpcResponse::error(
                                        req.id,
                                        -32602,
                                        &format!("Schema validation failed: {}", e),
                                    );
                                    let res_str = format!("{}\n", serde_json::to_string(&res).unwrap());
                                    let _ = stream.write_all(res_str.as_bytes());
                                }
                            }
                        }
                        Err(e) => {
                            log::error!("Failed to parse request: {}", e);
                        }
                    }
                }
            }
            Err(e) => {
                log::error!("IPC Error: {}", e);
                break;
            }
        }
    }
}

fn main() {
    env_logger::init();
    log::info!("Starting Astra Core...");
    
    let socket_path = &config::CONFIG.core.socket_path;
    let db_path = &config::CONFIG.core.db_path;

    if fs::metadata(socket_path).is_ok() {
        fs::remove_file(socket_path).unwrap();
    }

    use std::sync::Arc;
    use std::sync::Mutex;
    let db = Arc::new(Mutex::new(Db::new(db_path).expect("Failed to initialize SQLite db")));
    let mut state = SystemState::new();
    let (event_tx, event_rx): (Sender<EventEnvelope>, Receiver<EventEnvelope>) = unbounded();

    let listener = UnixListener::bind(socket_path).unwrap();
    log::info!("Listening on {}", socket_path);

    let tx_clone = event_tx.clone();
    let clients = Arc::new(Mutex::new(Vec::<Sender<String>>::new()));
    let clients_clone_accept = Arc::clone(&clients);

    std::thread::spawn(move || {
        for stream in listener.incoming() {
            match stream {
                Ok(stream) => {
                    let mut stream_write = stream
                        .try_clone()
                        .expect("Failed to clone stream for writing");
                    let stream_read = stream; // Original for reading

                    let (tx, rx) = unbounded::<String>();
                    clients_clone_accept.lock().unwrap().push(tx);

                    // Dedicated sender thread for this client
                    std::thread::spawn(move || {
                        while let Ok(msg) = rx.recv() {
                            if let Err(_) = stream_write.write_all(msg.as_bytes()) {
                                break;
                            }
                        }
                    });

                    let tx_event = tx_clone.clone();
                    std::thread::spawn(move || handle_client(stream_read, tx_event));
                }
                Err(err) => {
                    log::error!("Connection failed: {}", err);
                    break;
                }
            }
        }
    });

    log::info!("Event Loop started.");
    let loop_tx = event_tx.clone();

    // Start the GameMode watcher
    gamemode::start_watcher(event_tx.clone());

    if matches!(gamemode::is_game_mode_enabled(), Some(true)) {
        let _ = event_tx.send(EventEnvelope {
            schema_version: 1,
            event: "system.suspend".to_string(),
            timestamp: now_secs(),
            source: "startup".to_string(),
            data: events::EventPayload::SystemSuspend { reason: "gamemode_active".to_string() },
        });
    }

    loop {
        match event_rx.recv() {
            Ok(event) => {
                // Async persistence
                let db_clone = Arc::clone(&db);
                let event_clone = event.clone();
                std::thread::spawn(move || {
                    if let Ok(db_lock) = db_clone.lock() {
                        if let Err(e) = db_lock.insert_event(&event_clone) {
                            log::error!("Failed to log event: {}", e);
                        }
                    }
                });

                // Async broadcast via dedicated sender threads
                {
                    let mut dead_clients = vec![];
                    if let Ok(mut clients_lock) = clients.lock() {
                        let msg = format!("{}\n", serde_json::to_string(&event).unwrap());
                        for (i, tx) in clients_lock.iter_mut().enumerate() {
                            if let Err(_) = tx.send(msg.clone()) {
                                dead_clients.push(i);
                            }
                        }
                        for i in dead_clients.into_iter().rev() {
                            clients_lock.remove(i);
                        }
                    }
                }

                if let events::EventPayload::ToolRequest { task_id, tool_name, args, danger_tier } = &event.data {
                    let needs_confirmation = if let Some(task) = state.tasks.get(task_id) {
                        task.intent.as_ref().map(|i| i.requires_confirmation).unwrap_or(true)
                    } else {
                        true
                    };

                    // Also check danger tier (heuristically)
                    let mut is_dangerous = danger_tier.as_deref().unwrap_or("") == "high";
                    
                    if tool_name == "run_shell" {
                        let cmd = args.get("cmd").and_then(|v| v.as_str()).unwrap_or("");
                        if !is_shell_safe(cmd) {
                            is_dangerous = true;
                        }
                    }

                    if needs_confirmation || is_dangerous {
                        log::info!("Tool {} requires confirmation (dangerous: {})", tool_name, is_dangerous);
                        let pending_id = format!("pend_{}", now_secs());
                        let conf_env = EventEnvelope {
                            schema_version: 1,
                            event: "tool.confirmation_required".to_string(),
                            timestamp: now_secs(),
                            source: "core".to_string(),
                            data: events::EventPayload::ToolConfirmationRequired {
                                task_id: task_id.clone(),
                                tool_name: tool_name.clone(),
                                args: args.clone(),
                                pending_id,
                            },
                        };
                        let _ = loop_tx.send(conf_env);
                    } else {
                        log::info!("Executing Tool: {} for Task: {}", tool_name, task_id);
                        let tool_name = tool_name.clone();
                        let args = args.clone();
                        let task_id = task_id.clone();
                        let loop_tx = loop_tx.clone();
                        
                        std::thread::spawn(move || {
                            match tools::runner::execute_tool(&tool_name, &args) {
                                Ok(result) => {
                                    let comp_env = EventEnvelope {
                                        schema_version: 1,
                                        event: "tool.completed".to_string(),
                                        timestamp: now_secs(),
                                        source: "tool_runner".to_string(),
                                        data: events::EventPayload::ToolResult {
                                            task_id,
                                            tool_name,
                                            result,
                                        },
                                    };
                                    let _ = loop_tx.send(comp_env);
                                }
                                Err(e) => {
                                    log::error!("Tool Error: {}", e);
                                    let fail_env = EventEnvelope {
                                        schema_version: 1,
                                        event: "tool.rejected".to_string(),
                                        timestamp: now_secs(),
                                        source: "tool_runner".to_string(),
                                        data: events::EventPayload::ToolRejected {
                                            task_id,
                                            tool_name,
                                            reason: e,
                                        },
                                    };
                                    let _ = loop_tx.send(fail_env);
                                }
                            }
                        });
                    }
                }

                if let events::EventPayload::ToolConfirmed { pending_id, .. } = &event.data {
                    if let Some(pending) = state.pending_executions.get(pending_id) {
                        log::info!("Executing Confirmed Tool: {} for Task: {}", pending.tool_name, pending.task_id);
                        let pending = pending.clone();
                        let loop_tx = loop_tx.clone();
                        
                        std::thread::spawn(move || {
                            match tools::runner::execute_tool(&pending.tool_name, &pending.args) {
                                Ok(result) => {
                                    let comp_env = EventEnvelope {
                                        schema_version: 1,
                                        event: "tool.completed".to_string(),
                                        timestamp: now_secs(),
                                        source: "tool_runner".to_string(),
                                        data: events::EventPayload::ToolResult {
                                            task_id: pending.task_id.clone(),
                                            tool_name: pending.tool_name.clone(),
                                            result,
                                        },
                                    };
                                    let _ = loop_tx.send(comp_env);
                                }
                                Err(e) => {
                                    let fail_env = EventEnvelope {
                                        schema_version: 1,
                                        event: "task.failed".to_string(),
                                        timestamp: now_secs(),
                                        source: "tool_runner".to_string(),
                                        data: events::EventPayload::TaskFailed {
                                            task_id: pending.task_id.clone(),
                                            error: e.to_string(),
                                            retryable: false,
                                        },
                                    };
                                    let _ = loop_tx.send(fail_env);
                                }
                            }
                        });
                    }
                }

                if let events::EventPayload::ToolDenied { pending_id, reason, .. } = &event.data {
                    if let Some(pending) = state.pending_executions.get(pending_id) {
                        log::info!("Tool Denied: {} for Task: {}", pending.tool_name, pending.task_id);
                        let rej_env = EventEnvelope {
                            schema_version: 1,
                            event: "tool.rejected".to_string(),
                            timestamp: now_secs(),
                            source: "core".to_string(),
                            data: events::EventPayload::ToolRejected {
                                task_id: pending.task_id.clone(),
                                tool_name: pending.tool_name.clone(),
                                reason: format!("User denied: {}", reason),
                            },
                        };
                        let _ = loop_tx.send(rej_env);
                    }
                }

                if let events::EventPayload::SystemSuspend { .. } = &event.data {
                    std::thread::spawn(|| stop_heavy_components());
                    // Interrupt all active tasks
                    for (task_id, task) in state.tasks.iter_mut() {
                        if task.status == "executing" || task.status == "planning" {
                            let int_env = EventEnvelope {
                                schema_version: 1,
                                event: "task.interrupted".to_string(),
                                timestamp: now_secs(),
                                source: "core".to_string(),
                                data: events::EventPayload::TaskInterrupted {
                                    task_id: task_id.clone(),
                                    reason: "system_suspend".to_string(),
                                },
                            };
                            let _ = loop_tx.send(int_env);
                        }
                    }
                } else if let events::EventPayload::SystemResume {} = &event.data {
                    std::thread::spawn(|| start_heavy_components());
                    // Resume interrupted tasks
                    for (task_id, task) in state.tasks.iter_mut() {
                        if task.status == "interrupted" && task.interrupt_reason.as_deref() == Some("system_suspend") {
                            let upd_env = EventEnvelope {
                                schema_version: 1,
                                event: "task.updated".to_string(),
                                timestamp: now_secs(),
                                source: "core".to_string(),
                                data: events::EventPayload::TaskUpdated {
                                    task_id: task_id.clone(),
                                    status: "executing".to_string(),
                                    progress: None,
                                },
                            };
                            let _ = loop_tx.send(upd_env);
                        }
                    }
                }

                state = reducer::reduce(state, &event);
            }
            Err(_) => {
                log::info!("Event queue disconnected, shutting down.");
                break;
            }
        }
    }
}
