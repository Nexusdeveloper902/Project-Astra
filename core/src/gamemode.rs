use crate::events::EventEnvelope;
use crossbeam_channel::Sender;
use std::process::Command;
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

lazy_static::lazy_static! {
    static ref LAST_STATE: Mutex<Option<bool>> = Mutex::new(None);
}

pub fn start_watcher(event_tx: Sender<EventEnvelope>) {
    thread::spawn(move || {
        println!("[GameMode] Starting poll-based watcher...");

        loop {
            if let Some(enabled) = are_animations_enabled() {
                let mut last = LAST_STATE.lock().unwrap();
                if Some(enabled) != *last {
                    *last = Some(enabled);
                    if enabled {
                        println!("[GameMode] Animations ON (Game Mode OFF)");
                        send_event(&event_tx, "system.resume");
                    } else {
                        println!("[GameMode] Animations OFF (Game Mode ON)");
                        send_event(&event_tx, "system.suspend");
                    }
                }
            }

            thread::sleep(Duration::from_secs(2));
        }
    });
}

pub fn is_game_mode_enabled() -> Option<bool> {
    are_animations_enabled().map(|enabled| !enabled)
}

fn are_animations_enabled() -> Option<bool> {
    let output = Command::new("hyprctl")
        .arg("getoption")
        .arg("animations:enabled")
        .output()
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    for line in stdout.lines() {
        if line.starts_with("int: ") {
            let val = line.trim_start_matches("int: ").trim();
            return Some(val == "1");
        }
    }
    None
}

fn send_event(tx: &Sender<EventEnvelope>, event_name: &str) {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();
    let env = EventEnvelope {
        event: event_name.to_string(),
        timestamp,
        source: "gamemode_watcher".to_string(),
        data: serde_json::json!({}),
    };
    let _ = tx.send(env);
}
