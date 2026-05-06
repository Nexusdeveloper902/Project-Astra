use std::os::unix::net::UnixStream;
use std::io::{Write, Read, BufRead, BufReader};
use serde_json::{json, Value};
use tauri::{AppHandle, Manager, Emitter};

#[tauri::command]
fn send_input(text: String) -> Result<String, String> {
    let mut stream = UnixStream::connect("/tmp/astra.sock").map_err(|e| format!("Failed to connect to core: {}", e))?;
    
    let req = json!({
        "jsonrpc": "2.0",
        "id": "ui_001",
        "method": "ui.input",
        "params": {
            "text": text,
            "context": {"active_app": "Astra HUD"}
        }
    });
    
    let req_str = format!("{}\n", serde_json::to_string(&req).unwrap());
    stream.write_all(req_str.as_bytes()).map_err(|e| format!("Failed to send: {}", e))?;
    
    let mut buffer = [0; 4096];
    let size = stream.read(&mut buffer).unwrap_or(0);
    let res_str = String::from_utf8_lossy(&buffer[..size]).to_string();
    
    Ok(res_str)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let app_handle = app.handle().clone();
            std::thread::spawn(move || {
                loop {
                    if let Ok(stream) = UnixStream::connect("/tmp/astra.sock") {
                        let mut reader = BufReader::new(stream);
                        let mut line = String::new();
                        while let Ok(bytes) = reader.read_line(&mut line) {
                            if bytes == 0 { break; }
                            if let Ok(event) = serde_json::from_str::<Value>(&line) {
                                if let Some(event_type) = event.get("event").and_then(|v| v.as_str()) {
                                    if event_type == "ui.output" {
                                        if let Some(data) = event.get("data") {
                                            if let Some(text) = data.get("text").and_then(|v| v.as_str()) {
                                                let _ = app_handle.emit("astra-message", text);
                                            }
                                        }
                                    }
                                }
                            }
                            line.clear();
                        }
                    }
                    std::thread::sleep(std::time::Duration::from_secs(1));
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![send_input])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
