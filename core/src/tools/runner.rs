use serde_json::{json, Value};
use std::process::Command;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use chrono::Local;
use rand::{distributions::Alphanumeric, Rng};

pub fn execute_tool(tool_name: &str, args: &Value) -> Result<Value, String> {
    match tool_name {
        "run_shell" => {
            if let Some(cmd_str) = args.get("cmd").and_then(|v| v.as_str()) {
                let blocked = ["rm -rf /", "mkfs", "dd if=/dev/zero", ":(){ :|:& };:"];
                for b in blocked {
                    if cmd_str.contains(b) {
                        return Err(format!("Command contains blocked pattern: {}", b));
                    }
                }

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
                let vault_dir = &crate::config::CONFIG.orchestrator.vault_dir;
                let category = args.get("category").and_then(|v| v.as_str()).unwrap_or("general");
                let tags = args.get("tags").and_then(|v| v.as_array());
                let confidence = args.get("confidence").and_then(|v| v.as_f64()).unwrap_or(1.0);
                
                let target_dir = PathBuf::from(vault_dir).join(category);
                fs::create_dir_all(&target_dir).map_err(|e| format!("Failed to create directory {:?}: {}", target_dir, e))?;
                
                let timestamp = Local::now().format("%Y%m%d_%H%M%S").to_string();
                let random_suffix: String = rand::thread_rng()
                    .sample_iter(&Alphanumeric)
                    .take(6)
                    .map(char::from)
                    .collect();
                
                let filename = format!("mem_{}_{}.md", timestamp, random_suffix);
                let filepath = target_dir.join(&filename);
                
                let mut tags_str = String::new();
                if let Some(t_array) = tags {
                    let t_vec: Vec<String> = t_array.iter()
                        .filter_map(|v| v.as_str())
                        .map(|s| s.to_string())
                        .collect();
                    tags_str = format!("[{}]", t_vec.join(", "));
                }

                let yaml_frontmatter = format!(
"---
id: mem_{}_{}
timestamp: {}
tags: {}
source: auto
confidence: {}
---

{}
", timestamp, random_suffix, Local::now().to_rfc3339(), tags_str, confidence, content);

                fs::write(&filepath, yaml_frontmatter).map_err(|e| format!("Failed to write to {:?}: {}", filepath, e))?;
                
                Ok(json!({
                    "status": "success",
                    "path": filepath.to_string_lossy(),
                    "filename": filename
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
