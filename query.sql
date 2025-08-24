
-- A parent scans their card, their token value will be read and students related to them will be extracted
SELECT g.id AS guardian_id, s.id AS student_id, s.first_name, s.last_name, s.group_id
FROM tokens t
JOIN guardians g ON g.id = t.guardian_id
JOIN guardian_students gs ON gs.guardian_id = g.id
JOIN students s ON s.id = gs.student_id
WHERE t.token_value = "tokken-Safi"
  AND t.active = 1
  AND s.active = 1;

INSERT INTO pickups (token_id, requested_by)
SELECT t.id, NULL
FROM tokens t
WHERE t.token_value = "tokken-Safi" AND t.active = 1;

INSERT INTO pickup_students (pickup_id, student_id)
SELECT 1, s.id
FROM tokens t
JOIN guardians g ON g.id = t.guardian_id
JOIN guardian_students gs ON gs.guardian_id = g.id
JOIN students s ON s.id = gs.student_id
WHERE t.token_value = "tokken-Safi" AND s.active = 1;

SELECT ps.pickup_id,
       s.id AS student_id,
       s.first_name || ' ' || s.last_name AS student,
       p.requested_at,
       ps.status
FROM pickup_students ps
JOIN students s ON s.id = ps.student_id
JOIN pickups  p ON p.id = ps.pickup_id
WHERE s.group_id = 4
  AND ps.status IN ('PENDING','ACKED','READY_AT_EXIT')
ORDER BY p.requested_at DESC;

UPDATE pickup_students
SET status = "ACKED"
WHERE pickup_id = 1 AND student_id = 1;
