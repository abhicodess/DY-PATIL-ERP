# Enterprise ERP Architecture — Faculty Attendance System

## 1. Final Production Architecture
The ERP is transitioning from a monolithic Flask app into a modern, decoupled enterprise system:
- **Backend**: Flask API + PostgreSQL (Service-Repository Pattern)
- **Frontend**: React (SPA) + Vite
- **Async Workers**: Celery + Redis
- **Infrastructure**: Nginx (Reverse Proxy) + Gunicorn / Uvicorn

## 2. Directory Structure
```text
erp-enterprise/
├── api/                  # Flask REST APIs
│   └── v1/               # Versioned endpoints
├── services/             # Core business logic (Service Layer)
├── models/               # SQLAlchemy/Raw SQL database schemas
├── tasks/                # Celery background tasks
├── scripts/              # SQL migrations & utility scripts
├── static/               # Assets & built React files
├── templates/            # Legacy Jinja2 templates (phasing out)
├── frontend/             # React Source (Integrated via SPA)
└── app.py                # App Factory & Initialization
```

## 3. Attendance Workflow Redesign
**Enterprise Flow:**
1. **Auto-Load**: Faculty Dashboard fetches today's timetable via `/api/v1/faculty/timetable`.
2. **One-Click Start**: Clicking "Start" calls `/api/v1/attendance/initialize` which creates a `draft` session and pre-fetches the student list.
3. **Smart Marking**: "All Present" quick-toggle + "Absent" tap interface.
4. **Draft Save**: Auto-saves every 60 seconds to `/api/v1/attendance/submit?is_final=false`.
5. **Final Submission**: One-click finalize. Triggers asynchronous parent notifications via Celery.

## 4. Database Optimization Plan
- **Constraints**: Apply `UNIQUE(timetable_id, lecture_date)` to prevent duplicates.
- **Triggers**: Implement `guard_locked_session()` to prevent tampering after submission.
- **Indexing**: Add B-tree indexes on `faculty_id`, `student_id`, and `date`.
- **Audit**: Log all attendance changes to `attendance_audit` via SQL triggers for integrity.

## 5. React Migration Strategy
- **Service Layer**: Create `src/api/attendanceService.js` using Axios and Interceptors.
- **State Hooks**: Implement `useAttendance` to manage session state, loading, and optimistic updates.
- **Components**: Port Jinja templates to functional React components with Shadcn/UI for a premium feel.
- **Real-time**: Integrate WebSocket (Socket.io) for live student count updates across devices.

## 6. Performance Roadmap
- **Batching**: Use SQL `COPY` or multi-row `INSERT ON CONFLICT` for bulk attendance.
- **Caching**: Use Redis to cache the "Today's Timetable" for each faculty.
- **Pagination**: Strictly enforce API-level pagination for all student lists and history tables.
- **Query Optimization**: Remove N+1 problems by using `JOIN` with specific columns instead of `SELECT *`.

## 7. Security Checklist
- [x] **RBAC**: Role-Based Access Control on every API endpoint.
- [x] **CSRF**: Token validation on all non-GET requests.
- [x] **Audit Logging**: Mandatory logging for every administrative/faculty action.
- [x] **Rate Limiting**: Apply via Flask-Limiter for Auth and Sensitive APIs.
- [x] **Sanitization**: SQL Parameterization (already in use via pg_wrapper).

## 8. Implementation Roadmap
1. **API Migration**: Register V1 Blueprints (Done).
2. **Service Layer**: Move logic from app.py to files in `services/` (Ongoing).
3. **DB Hardening**: Execute `scripts/db_hardening.sql`.
4. **Cellery Setup**: Start Redis and Celery worker.
5. **React Porting**: Connect the existing prototype pages to the new APIs.
