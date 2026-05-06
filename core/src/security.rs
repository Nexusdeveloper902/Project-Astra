use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct CapabilityToken {
    pub token_id: String,
    pub task_id: String,
    pub tool: String,
    pub capabilities: Vec<String>,
    pub issued_at: u64,
    pub expires_at: u64,
    pub origin: String,
}

impl CapabilityToken {
    pub fn is_valid(&self, current_time: u64, requested_tool: &str) -> bool {
        if current_time > self.expires_at {
            return false;
        }
        if self.tool != requested_tool {
            return false;
        }
        true
    }
}
