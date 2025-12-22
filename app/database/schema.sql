-- MIDI Deck Database Schema
-- SQLite schema for configuration and session management
-- This file serves as a reference for the database structure
-- Actual table creation will be done via SQLAlchemy in Phase 2

-- Configuration table for application settings
CREATE TABLE IF NOT EXISTS config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    value_type TEXT DEFAULT 'string', -- string, integer, float, boolean, json
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hardware outputs (speakers, headphones, etc.)
CREATE TABLE IF NOT EXISTS hardware_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,           -- e.g., "SpeakerOut", "HeadphoneOut"
    device_name TEXT NOT NULL,           -- PulseAudio device name
    description TEXT,                     -- User-friendly description
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Virtual sinks/channels
CREATE TABLE IF NOT EXISTS virtual_sinks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_number INTEGER UNIQUE NOT NULL, -- 1, 2, 3, 4 (fader mapping)
    name TEXT UNIQUE NOT NULL,              -- e.g., "MainSink", "WebSink"
    description TEXT,                        -- User-friendly description
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- MIDI button mappings
CREATE TABLE IF NOT EXISTS midi_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    midi_note INTEGER UNIQUE NOT NULL,   -- MIDI note number (36-50)
    sink_id INTEGER NOT NULL,            -- Reference to virtual_sinks
    action TEXT NOT NULL,                 -- 'speaker', 'headphone', 'mute'
    description TEXT,
    FOREIGN KEY (sink_id) REFERENCES virtual_sinks(id) ON DELETE CASCADE
);

-- Sessions for save/restore functionality
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_current BOOLEAN DEFAULT 0,        -- Only one session can be current
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Session state: sink volumes
CREATE TABLE IF NOT EXISTS session_volumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    sink_id INTEGER NOT NULL,
    volume REAL NOT NULL,                 -- 0.0 to 1.0
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (sink_id) REFERENCES virtual_sinks(id) ON DELETE CASCADE,
    UNIQUE(session_id, sink_id)
);

-- Session state: sink connections
CREATE TABLE IF NOT EXISTS session_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    sink_id INTEGER NOT NULL,
    output_id INTEGER NOT NULL,
    is_connected BOOLEAN DEFAULT 1,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (sink_id) REFERENCES virtual_sinks(id) ON DELETE CASCADE,
    FOREIGN KEY (output_id) REFERENCES hardware_outputs(id) ON DELETE CASCADE,
    UNIQUE(session_id, sink_id, output_id)
);

-- Session state: mute status
CREATE TABLE IF NOT EXISTS session_mutes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    sink_id INTEGER NOT NULL,
    is_muted BOOLEAN DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (sink_id) REFERENCES virtual_sinks(id) ON DELETE CASCADE,
    UNIQUE(session_id, sink_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_config_key ON config(key);
CREATE INDEX IF NOT EXISTS idx_midi_note ON midi_mappings(midi_note);
CREATE INDEX IF NOT EXISTS idx_session_current ON sessions(is_current);
CREATE INDEX IF NOT EXISTS idx_session_volumes ON session_volumes(session_id, sink_id);
CREATE INDEX IF NOT EXISTS idx_session_connections ON session_connections(session_id, sink_id);

-- Trigger to ensure only one current session
CREATE TRIGGER IF NOT EXISTS ensure_single_current_session
    BEFORE UPDATE ON sessions
    WHEN NEW.is_current = 1
BEGIN
    UPDATE sessions SET is_current = 0 WHERE is_current = 1;
END;
