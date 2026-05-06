use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct EventEnvelope {
    pub event: String,
    pub timestamp: u64,
    pub source: String,
    #[serde(default)]
    pub data: Value,
}
