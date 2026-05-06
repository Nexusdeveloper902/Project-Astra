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
