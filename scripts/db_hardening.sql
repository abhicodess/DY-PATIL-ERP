-- Database Hardening for Enterprise ERP
-- Phase 4: Constraints, Indexes, and Triggers

-- 1. Session Constraints
-- Prevent duplicate attendance for same lecture on same day
ALTER TABLE attendance_sessions 
ADD CONSTRAINT unique_lecture_session UNIQUE(timetable_id, lecture_date);

-- 2. Performance Indexes
CREATE INDEX IF NOT EXISTS idx_attendance_lecture_id ON attendance(lecture_id);
CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);
CREATE INDEX IF NOT EXISTS idx_timetable_faculty_day ON timetable(faculty_id, day);

-- 3. Attendance Locking Trigger
CREATE OR REPLACE FUNCTION guard_locked_session()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if session is locked
    IF EXISTS (
        SELECT 1 FROM attendance_sessions 
        WHERE id = NEW.lecture_id AND (status = 'submitted' OR is_locked = TRUE)
    ) THEN
        RAISE EXCEPTION 'This attendance session is locked and cannot be modified.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to attendance table
DROP TRIGGER IF EXISTS trg_guard_attendance_lock ON attendance;
CREATE TRIGGER trg_guard_attendance_lock
BEFORE INSERT OR UPDATE OR DELETE ON attendance
FOR EACH ROW EXECUTE FUNCTION guard_locked_session();

-- 4. Audit Logging Trigger (Example for attendance)
CREATE OR REPLACE FUNCTION log_attendance_change()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO attendance_audit (faculty_id, session_id, student_id, action, prev_status, new_status)
    VALUES (
        COALESCE(NEW.faculty_id, OLD.faculty_id),
        COALESCE(NEW.lecture_id, OLD.lecture_id),
        COALESCE(NEW.student_id, OLD.student_id),
        TG_OP,
        CASE WHEN TG_OP = 'UPDATE' THEN OLD.status ELSE NULL END,
        CASE WHEN TG_OP <> 'DELETE' THEN NEW.status ELSE NULL END
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_log_attendance_change
AFTER INSERT OR UPDATE OR DELETE ON attendance
FOR EACH ROW EXECUTE FUNCTION log_attendance_change();
