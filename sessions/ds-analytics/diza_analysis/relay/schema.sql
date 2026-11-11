CREATE TABLE IF NOT EXISTS relay_settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS relay_notices(
    id TEXT PRIMARY KEY, title TEXT NOT NULL, current_version INTEGER NOT NULL,
    source TEXT NOT NULL, created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS relay_notice_versions(
    notice_id TEXT NOT NULL REFERENCES relay_notices(id), version INTEGER NOT NULL,
    content TEXT NOT NULL, reason TEXT NOT NULL, published_by TEXT NOT NULL,
    published_at REAL NOT NULL, title TEXT NOT NULL, PRIMARY KEY(notice_id,version)
);
CREATE TABLE IF NOT EXISTS relay_residents(
    id TEXT PRIMARY KEY, name TEXT NOT NULL, language TEXT NOT NULL,
    opt_in INTEGER NOT NULL CHECK(opt_in IN (0,1)), source TEXT NOT NULL, created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS relay_records(
    id TEXT PRIMARY KEY, resident_id TEXT NOT NULL REFERENCES relay_residents(id),
    notice_id TEXT NOT NULL REFERENCES relay_notices(id), draft_step TEXT, draft_version INTEGER,
    assistance_needed INTEGER, assistance_details TEXT, assistance_confirmed INTEGER NOT NULL DEFAULT 0,
    clarification_version INTEGER, last_attempt_at REAL, updated REAL NOT NULL,
    UNIQUE(resident_id,notice_id)
);
CREATE TABLE IF NOT EXISTS relay_confirmations(
    record_id TEXT NOT NULL REFERENCES relay_records(id), version INTEGER NOT NULL,
    next_step TEXT NOT NULL, channel TEXT NOT NULL, confirmed_at REAL NOT NULL,
    PRIMARY KEY(record_id,version)
);
CREATE TABLE IF NOT EXISTS relay_assistance(
    id TEXT PRIMARY KEY, record_id TEXT NOT NULL UNIQUE REFERENCES relay_records(id),
    details TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('requested','accepted','completed')),
    owner TEXT, revision INTEGER NOT NULL DEFAULT 1, requested_version INTEGER NOT NULL,
    created REAL NOT NULL, updated REAL NOT NULL, completed_at REAL
);
CREATE TABLE IF NOT EXISTS relay_followups(
    record_id TEXT NOT NULL REFERENCES relay_records(id), version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('open','complete','superseded')),
    reason TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
    PRIMARY KEY(record_id,version)
);
CREATE TABLE IF NOT EXISTS relay_attempts(
    id TEXT PRIMARY KEY, record_id TEXT NOT NULL REFERENCES relay_records(id),
    version INTEGER NOT NULL, channel TEXT NOT NULL, status TEXT NOT NULL,
    call_id TEXT UNIQUE, created REAL NOT NULL, ended REAL
);
CREATE TABLE IF NOT EXISTS relay_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT, notice_id TEXT NOT NULL,
    version INTEGER NOT NULL, type TEXT NOT NULL, detail TEXT NOT NULL, ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS relay_receipts(
    scope TEXT NOT NULL, key TEXT NOT NULL, request_hash TEXT NOT NULL,
    result TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(scope,key)
);
CREATE INDEX IF NOT EXISTS relay_records_notice ON relay_records(notice_id);
CREATE INDEX IF NOT EXISTS relay_events_record ON relay_events(record_id,id);
CREATE INDEX IF NOT EXISTS relay_attempts_record ON relay_attempts(record_id,created);
