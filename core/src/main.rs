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
    loop {
        match stream.read(&mut buffer) {
            Ok(size) => {
                if size == 0 {
                    break;
                }
                let req_str = String::from_utf8_lossy(&buffer[..size]);
                for line in req_str.lines() {
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

                            let env = EventEnvelope {
                                event: req.method.clone(),
                                timestamp: now_secs(),
                                source: "ipc".to_string(),
                                data: req.params.clone(),
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

    let db = Db::new(db_path).expect("Failed to initialize SQLite db");
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
            event: "system.suspend".to_string(),
            timestamp: now_secs(),
            source: "startup".to_string(),
            data: serde_json::json!({ "reason": "gamemode_active" }),
        });
    }

    loop {
        match event_rx.recv() {
            Ok(event) => {
                log::info!("EVENT: {} from {}", event.event, event.source);
                if let Err(e) = db.insert_event(&event) {
                    log::error!("Failed to log event: {}", e);
                }

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

                if event.event == "tool.requested" {
                    let task_id = event
                        .data
                        .get("task_id")
                        .and_then(|v| v.as_str())
                        .unwrap_or("unknown");
                    let tool_name = event
                        .data
                        .get("tool_name")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    let args = event.data.get("args").unwrap_or(&serde_json::Value::Null);

                    log::info!("Executing Tool: {} for Task: {}", tool_name, task_id);
                    match tools::runner::execute_tool(tool_name, args) {
                        Ok(result) => {
                            let comp_env = EventEnvelope {
                                event: "tool.completed".to_string(),
                                timestamp: now_secs(),
                                source: "tool_runner".to_string(),
                                data: serde_json::json!({
                                    "task_id": task_id,
                                    "tool_name": tool_name,
                                    "result": result
                                }),
                            };
                            let _ = loop_tx.send(comp_env);
                        }
                        Err(e) => {
                            let err_env = EventEnvelope {
                                event: "tool.failed".to_string(),
                                timestamp: now_secs(),
                                source: "tool_runner".to_string(),
                                data: serde_json::json!({
                                    "task_id": task_id,
                                    "tool_name": tool_name,
                                    "error": e
                                }),
                            };
                            let _ = loop_tx.send(err_env);
                        }
                    }
                }

                if event.event == "system.suspend" {
                    stop_heavy_components();
                } else if event.event == "system.resume" {
                    start_heavy_components();
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
