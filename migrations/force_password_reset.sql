-- 1. Add must_change_password column if it does not exist
ALTER TABLE public.students ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;
ALTER TABLE public.faculty ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;

-- 2. Force reset for all faculty and students that still have default passwords or hashes
-- We can set must_change_password = TRUE for anyone whose password matches standard default passwords or hashes.
-- Since default passwords were "student123", "faculty123" or values generated in imports/env files,
-- let's set must_change_password to TRUE for all existing accounts to ensure a clean, secure go-live.
UPDATE public.students SET must_change_password = TRUE;
UPDATE public.faculty SET must_change_password = TRUE;
