PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS hotel_rooms(number TEXT PRIMARY KEY, floor INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS hotel_staff(id TEXT PRIMARY KEY, name TEXT NOT NULL, department TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS hotel_sessions(
    id TEXT PRIMARY KEY, token TEXT NOT NULL, room TEXT NOT NULL REFERENCES hotel_rooms(number),
    language TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
    pending TEXT, created REAL NOT NULL, updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS hotel_messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES hotel_sessions(id),
    role TEXT NOT NULL, text TEXT NOT NULL, created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS hotel_tickets(
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT REFERENCES hotel_sessions(id),
    room TEXT NOT NULL REFERENCES hotel_rooms(number), category TEXT NOT NULL,
    department TEXT NOT NULL, urgency TEXT NOT NULL, summary TEXT NOT NULL,
    quote TEXT NOT NULL, language TEXT NOT NULL, access_ok INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'new', assignee TEXT REFERENCES hotel_staff(id),
    revision INTEGER NOT NULL DEFAULT 1, created REAL NOT NULL, updated REAL NOT NULL,
    completed REAL
);
CREATE TABLE IF NOT EXISTS hotel_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER REFERENCES hotel_tickets(id),
    session_id TEXT REFERENCES hotel_sessions(id), type TEXT NOT NULL,
    detail TEXT NOT NULL, created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS hotel_receipts(
    scope TEXT NOT NULL, key TEXT NOT NULL, digest TEXT NOT NULL, result TEXT NOT NULL,
    PRIMARY KEY(scope,key)
);
CREATE INDEX IF NOT EXISTS hotel_messages_session ON hotel_messages(session_id,id);
CREATE INDEX IF NOT EXISTS hotel_ticket_room ON hotel_tickets(room,category,created);
