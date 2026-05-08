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
        Ok(Db { conn })
    }

    pub fn insert_event(&self, env: &EventEnvelope) -> Result<()> {
        let data_str = serde_json::to_string(&env.data).unwrap_or_default();
        self.conn.execute(
            "INSERT INTO events (event_type, timestamp, source, data) VALUES (?1, ?2, ?3, ?4)",
            params![env.event, env.timestamp, env.source, data_str],
        )?;
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
