CHANGELOG_DATA = {
  "versions": [
    {
      "version":      "1.3.0",
      "released":     "2025-05-30",
      "status":       "stable",
      "breaking":     False,
      "changes": {
        "added":      [
          "POST /api/v1/reports/generate — async report generation engine",
          "GET  /api/v1/reports/status/{job_id} — report polling endpoint",
          "GET  /api/v1/reports/download/{job_id} — report file download",
          "WebSocket /attendance namespace — real-time attendance count streaming",
          "GET  /api/v1/tenant/info — public tenant branding endpoint"
        ],
        "changed":    [
          "GET /api/v1/attendance/summary — response now includes subject_wise breakdown array (non-breaking, new field added)",
          "POST /api/v1/auth/login — response now includes tenant_slug claim in JWT (non-breaking)"
        ],
        "deprecated": [],
        "removed":    [],
        "fixed":      [],
        "security":   [
          "JWT_SECRET_KEY now required env var — hardcoded fallback removed",
          "CSP nonce added to all HTML responses"
        ]
      }
    },
    {
      "version":      "1.2.0",
      "released":     "2025-03-10",
      "status":       "stable",
      "breaking":     False,
      "changes": {
        "added":      [
          "Multi-tenant support — all endpoints now scoped to subdomain tenant",
          "POST /api/v1/attendance/submit?is_final — final submission flag",
          "Celery async task queues (critical, default, bulk, scheduled)"
        ],
        "changed":    [],
        "deprecated": [
          "GET /api/v1/students/list — use GET /api/v1/students instead. Will be removed in v2.0.0. Sunset: 2026-01-01."
        ],
        "removed":    [],
        "fixed":      [],
        "security":   []
      }
    },
    {
      "version":      "1.1.0",
      "released":     "2025-01-15",
      "status":       "stable",
      "breaking":     False,
      "changes": {
        "added":      [
          "RBAC role enforcement on all endpoints",
          "Redis caching layer for timetable and student list endpoints",
          "Rate limiting: 200 req/min global, 10 req/min on auth endpoints"
        ],
        "changed":    [],
        "deprecated": [],
        "removed":    [],
        "fixed":      [
          "GET /api/v1/results — N+1 query replaced with JOIN (10x faster)"
        ],
        "security":   []
      }
    },
    {
      "version":      "1.0.0",
      "released":     "2024-11-01",
      "status":       "stable",
      "breaking":     False,
      "changes": {
        "added":      [
          "Initial API release",
          "Auth, Students, Faculty, Attendance, Results, Timetable blueprints"
        ],
        "changed":    [],
        "deprecated": [],
        "removed":    [],
        "fixed":      [],
        "security":   []
      }
    }
  ],
  "deprecated_versions": [],
  "sunset_versions":     [],
  "latest_stable":       "1.3.0",
  "migration_guides": {
    "v1_to_v2": "https://yourerp.com/docs/migration/v1-to-v2"
  }
}
