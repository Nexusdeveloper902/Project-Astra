use serde_json::{json, Value};
use std::process::Command;
use std::fs::OpenOptions;
use std::io::Write;

pub fn execute_tool(tool_name: &str, args: &Value) -> Result<Value, String> {
    match tool_name {
        "run_shell" => {
            if let Some(cmd_str) = args.get("cmd").and_then(|v| v.as_str()) {
                let output = Command::new("bash")
                    .arg("-c")
                    .arg(cmd_str)
                    .output()
                    .map_err(|e| e.to_string())?;

                let stdout = String::from_utf8_lossy(&output.stdout).to_string();
                let stderr = String::from_utf8_lossy(&output.stderr).to_string();
                
                Ok(json!({
                    "stdout": stdout,
                    "stderr": stderr,
                    "status_code": output.status.code().unwrap_or(-1)
                }))
            } else {
                Err("Missing 'cmd' argument".to_string())
            }
        }
        "save_memory" => {
            if let Some(content) = args.get("content").and_then(|v| v.as_str()) {
                let mut file = OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open("/home/jperez/Astra/vault_memories.md")
                    .map_err(|e| e.to_string())?;
                
                writeln!(file, "\n{}", content).map_err(|e| e.to_string())?;
                
                Ok(json!({
                    "status": "success",
                    "message": "Memory saved successfully to vault_memories.md"
                }))
            } else {
                Err("Missing 'content' argument".to_string())
            }
        }
        _ => Err(format!("Unknown tool: {}", tool_name)),
    }
}
