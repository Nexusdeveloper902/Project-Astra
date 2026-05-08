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

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn run_shell_executes_command_and_returns_output() {
        let result = execute_tool("run_shell", &json!({"cmd": "printf astra"})).unwrap();

        assert_eq!(result["stdout"], "astra");
        assert_eq!(result["stderr"], "");
        assert_eq!(result["status_code"], 0);
    }

    #[test]
    fn run_shell_reports_nonzero_status_code() {
        let result = execute_tool("run_shell", &json!({"cmd": "exit 7"})).unwrap();

        assert_eq!(result["status_code"], 7);
    }

    #[test]
    fn run_shell_requires_cmd_argument() {
        let error = execute_tool("run_shell", &json!({"command": "printf astra"})).unwrap_err();

        assert_eq!(error, "Missing 'cmd' argument");
    }

    #[test]
    fn save_memory_requires_content_argument_before_writing() {
        let error = execute_tool("save_memory", &json!({"text": "missing content"})).unwrap_err();

        assert_eq!(error, "Missing 'content' argument");
    }

    #[test]
    fn unknown_tool_returns_descriptive_error() {
        let error = execute_tool("missing_tool", &json!({})).unwrap_err();

        assert_eq!(error, "Unknown tool: missing_tool");
    }
}
