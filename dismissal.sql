PRAGMA foreign_keys = ON;

CREATE TABLE groups(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE students (
  id         INTEGER PRIMARY KEY,
  first_name TEXT NOT NULL,
  last_name  TEXT NOT NULL,
  grade      TEXT NOT NULL,
  group_id   INTEGER REFERENCES groups(id) ON DELETE SET NULL,
  active     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE guardians (
  id    INTEGER PRIMARY KEY,
  name  TEXT NOT NULL,
  phone TEXT DEFAULT 'None',
  email TEXT DEFAULT 'None'
);

-- link A guardian to a student (or students)
CREATE TABLE guardian_students (
  guardian_id INTEGER NOT NULL REFERENCES guardians(id) ON DELETE CASCADE,
  student_id  INTEGER NOT NULL REFERENCES students(id)  ON DELETE CASCADE,
  PRIMARY KEY (guardian_id, student_id)
);

-- Assigned to each guardian. Linked to students.
CREATE TABLE tokens (
  id           INTEGER PRIMARY KEY,
  token_value  TEXT NOT NULL UNIQUE,
  guardian_id  INTEGER NOT NULL REFERENCES guardians(id) ON DELETE CASCADE,
  active       INTEGER NOT NULL DEFAULT 1,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  revoked_at   TEXT DEFAULT 'None'
);

CREATE TABLE users (
  id            INTEGER PRIMARY KEY,
  username      TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  first_name    TEXT NOT NULL,
  last_name     TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('ADMIN','PROCTOR','TEACHER','DOOR')),
  group_id      INTEGER REFERENCES groups(id) ON DELETE SET NULL
);  

-- 7) Pickup request (one per scan)
CREATE TABLE pickups (
  id            INTEGER PRIMARY KEY,
  token_id      INTEGER NOT NULL REFERENCES tokens(id),
  requested_at  TEXT NOT NULL DEFAULT (datetime('now')),
  requested_by  INTEGER REFERENCES users(id), -- proctor user id; nullable for test
  status        TEXT NOT NULL DEFAULT 'PENDING'
                 CHECK (status IN ('PENDING','SENT')),
  note          TEXT DEFAULT 'None'
);

-- 8) Students on that pickup (supports siblings)
CREATE TABLE pickup_students (
  pickup_id   INTEGER NOT NULL REFERENCES pickups(id) ON DELETE CASCADE,
  student_id  INTEGER NOT NULL REFERENCES students(id),
  status      TEXT NOT NULL DEFAULT 'PENDING'
               CHECK (status IN ('PENDING','SENT')),
  sent_at     TEXT DEFAULT 'None',
  PRIMARY KEY (pickup_id, student_id)
);


-- Helpful indexes 
CREATE INDEX idx_students_group    ON students(group_id);
CREATE INDEX idx_users_group       ON users(group_id);
CREATE INDEX idx_tokens_guardian   ON tokens(guardian_id);
CREATE INDEX idx_pickups_token     ON pickups(token_id);
CREATE INDEX idx_pickup_students_s ON pickup_students(student_id);
