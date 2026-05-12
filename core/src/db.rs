use rusqlite::{params, Connection, Result};
use crate::events::EventEnvelope;
use std::path::Path;

pub struct Db {
    conn: Connection,
}

impl Db {
    pub fn new<P: AsRef<Path>>(path: P) -> Result<Self> {
        let conn = Connection::open(path)?;
        conn.execute(
            "CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                event_type TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                source TEXT NOT NULL,
                data TEXT NOT NULL
            )",
            [],
        )?;
        
        conn.execute(
            "CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                event_id INTEGER
            )",
            [],
        )?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS execution_contexts (
                id INTEGER PRIMARY KEY,
                context_id TEXT NOT NULL UNIQUE,
                session_id TEXT,
                task_id TEXT,
                model_id TEXT,
                temperature REAL,
                max_tokens INTEGER,
                prompt_template_version TEXT,
                tool_registry_version TEXT,
                planner_version TEXT,
                routing_decision TEXT,
                created_at INTEGER NOT NULL
            )",
            [],
        )?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS retrieved_memory_ids (
                id INTEGER PRIMARY KEY,
                context_id TEXT NOT NULL,
                memory_id TEXT NOT NULL,
                rank INTEGER,
                distance_score REAL,
                FOREIGN KEY(context_id) REFERENCES execution_contexts(context_id)
            )",
            [],
        )?;

        Ok(Db { conn })
    }

    pub fn insert_event(&self, env: &EventEnvelope) -> Result<()> {
        let data_str = serde_json::to_string(&env.data).unwrap_or_default();
        self.conn.execute(
            "INSERT INTO events (event_type, timestamp, source, data) VALUES (?1, ?2, ?3, ?4)",
            params![env.event, env.timestamp, env.source, data_str],
        )?;
        let event_id = self.conn.last_insert_rowid();

        if env.event == "ui.input" || env.event == "ui.output" {
            let role = if env.event == "ui.input" { "user" } else { "assistant" };
            let content = env.data.get("text").and_then(|v| v.as_str()).unwrap_or("");
            // Default session_id to "default" if not provided
            let session_id = env.data.get("session_id").and_then(|v| v.as_str()).unwrap_or("default");

            self.conn.execute(
                "INSERT INTO conversations (session_id, role, content, timestamp, event_id) VALUES (?1, ?2, ?3, ?4, ?5)",
                params![session_id, role, content, env.timestamp, event_id],
            )?;
        } else if env.event == "execution.context_captured" {
            let ctx = &env.data;
            let context_id = ctx.get("context_id").and_then(|v| v.as_str()).unwrap_or("unknown");
            let session_id = ctx.get("session_id").and_then(|v| v.as_str());
            let task_id = ctx.get("task_id").and_then(|v| v.as_str());
            let model_id = ctx.get("model_id").and_then(|v| v.as_str());
            let temperature = ctx.get("temperature").and_then(|v| v.as_f64());
            let max_tokens = ctx.get("max_tokens").and_then(|v| v.as_i64());
            let prompt_template_version = ctx.get("prompt_template_version").and_then(|v| v.as_str());
            let tool_registry_version = ctx.get("tool_registry_version").and_then(|v| v.as_str());
            let planner_version = ctx.get("planner_version").and_then(|v| v.as_str());
            let routing_decision = ctx.get("routing_decision").and_then(|v| v.as_str());

            self.conn.execute(
                "INSERT INTO execution_contexts (
                    context_id, session_id, task_id, model_id, temperature, max_tokens, 
                    prompt_template_version, tool_registry_version, planner_version, routing_decision, created_at
                ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
                params![
                    context_id, session_id, task_id, model_id, temperature, max_tokens,
                    prompt_template_version, tool_registry_version, planner_version, routing_decision, env.timestamp
                ],
            )?;

            if let Some(memories) = ctx.get("retrieved_memory_ids").and_then(|v| v.as_array()) {
                for (rank, mem) in memories.iter().enumerate() {
                    let memory_id = mem.as_str().unwrap_or("unknown");
                    self.conn.execute(
                        "INSERT INTO retrieved_memory_ids (context_id, memory_id, rank) VALUES (?1, ?2, ?3)",
                        params![context_id, memory_id, rank as i64],
                    )?;
                }
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn unique_db_path() -> std::path::PathBuf {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("astra_core_test_{}_{}.db", std::process::id(), unique))
    }

    #[test]
    fn new_creates_events_table() {
        let path = unique_db_path();
        let _db = Db::new(&path).expect("db should initialize");

        let conn = Connection::open(&path).unwrap();
        let table_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'events'",
                [],
                |row| row.get(0),
            )
            .unwrap();

        assert_eq!(table_count, 1);
        let _ = fs::remove_file(path);
    }

    #[test]
    fn insert_event_persists_event_fields_and_json_data() {
        let path = unique_db_path();
        let db = Db::new(&path).expect("db should initialize");
        let event = EventEnvelope {
            event: "tool.completed".to_string(),
            timestamp: 456,
            source: "test".to_string(),
            data: json!({"task_id": "task-1", "ok": true}),
        };

        db.insert_event(&event).expect("event should insert");
        drop(db);

        let conn = Connection::open(&path).unwrap();
        let row: (String, u64, String, String) = conn
            .query_row(
                "SELECT event_type, timestamp, source, data FROM events",
                [],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
            )
            .unwrap();

        assert_eq!(row.0, "tool.completed");
        assert_eq!(row.1, 456);
        assert_eq!(row.2, "test");
        assert_eq!(serde_json::from_str::<serde_json::Value>(&row.3).unwrap(), event.data);
        let _ = fs::remove_file(path);
    }
}
