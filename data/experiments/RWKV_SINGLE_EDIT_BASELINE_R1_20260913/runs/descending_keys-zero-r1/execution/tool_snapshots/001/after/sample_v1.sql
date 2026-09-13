PRAGMA user_version=1;
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT INTO settings VALUES ('theme', '"深色"');
INSERT INTO settings VALUES ('enabled', 'true');
