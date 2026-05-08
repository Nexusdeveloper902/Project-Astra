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

#[cfg(test)]
mod tests {
    use super::*;

    fn token() -> CapabilityToken {
        CapabilityToken {
            token_id: "token-1".to_string(),
            task_id: "task-1".to_string(),
            tool: "run_shell".to_string(),
            capabilities: vec!["read".to_string()],
            issued_at: 10,
            expires_at: 20,
            origin: "test".to_string(),
        }
    }

    #[test]
    fn token_is_valid_for_matching_tool_before_expiration() {
        assert!(token().is_valid(15, "run_shell"));
    }

    #[test]
    fn token_is_valid_at_exact_expiration_time() {
        assert!(token().is_valid(20, "run_shell"));
    }

    #[test]
    fn token_is_invalid_after_expiration() {
        assert!(!token().is_valid(21, "run_shell"));
    }

    #[test]
    fn token_is_invalid_for_different_tool() {
        assert!(!token().is_valid(15, "save_memory"));
    }
}
