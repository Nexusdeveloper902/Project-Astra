use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use lazy_static::lazy_static;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct CoreConfig {
    pub socket_path: String,
    pub db_path: String,
    pub toggle_script_path: String,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct OrchestratorConfig {
    pub vault_dir: String,
    pub vault_file: String,
    pub log_level: String,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct LlmConfig {
    pub server_url: String,
    pub default_max_tokens: u32,
    pub default_temperature: f32,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct MemoryConfig {
    pub embedder_type: String,
    pub embedder_model: String,
    pub embedder_dim: usize,
    pub index_rebuild_on_start: bool,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct HudConfig {
    pub always_on_top: bool,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct SecurityConfig {
    pub blocked_commands: Vec<String>,
    pub allowed_paths: Vec<String>,
    pub confirmation_timeout_secs: u32,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Config {
    pub core: CoreConfig,
    pub orchestrator: OrchestratorConfig,
    pub llm: LlmConfig,
    pub memory: MemoryConfig,
    pub hud: HudConfig,
    pub security: SecurityConfig,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            core: CoreConfig {
                socket_path: "/tmp/astra.sock".to_string(),
                db_path: "/tmp/astra.db".to_string(),
                toggle_script_path: "/home/jperez/.local/bin/astra-toggle".to_string(),
            },
            orchestrator: OrchestratorConfig {
                vault_dir: "/home/jperez/Astra/memories".to_string(),
                vault_file: "/home/jperez/Astra/vault_memories.md".to_string(),
                log_level: "INFO".to_string(),
            },
            llm: LlmConfig {
                server_url: "http://localhost:8080/v1".to_string(),
                default_max_tokens: 512,
                default_temperature: 0.7,
            },
            memory: MemoryConfig {
                embedder_type: "sentence-transformers".to_string(),
                embedder_model: "all-MiniLM-L6-v2".to_string(),
                embedder_dim: 384,
                index_rebuild_on_start: false,
            },
            hud: HudConfig {
                always_on_top: true,
            },
            security: SecurityConfig {
                blocked_commands: vec!["rm -rf /".to_string(), "mkfs".to_string(), "dd if=/dev/zero".to_string()],
                allowed_paths: vec!["/home/jperez".to_string(), "/tmp".to_string()],
                confirmation_timeout_secs: 30,
            },
        }
    }
}

pub fn load_config() -> Config {
    let mut config_path = PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/home/jperez".to_string()));
    config_path.push(".config/astra/config.toml");

    match fs::read_to_string(&config_path) {
        Ok(contents) => match toml::from_str(&contents) {
            Ok(config) => config,
            Err(e) => {
                log::error!("Failed to parse config file: {}. Falling back to default.", e);
                Config::default()
            }
        },
        Err(e) => {
            log::warn!("Failed to read config file: {}. Falling back to default.", e);
            Config::default()
        }
    }
}

lazy_static! {
    pub static ref CONFIG: Config = load_config();
}
