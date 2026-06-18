# API Deprecation Policy

## Versioning scheme
DY Patil ERP API uses MAJOR.MINOR.PATCH (SemVer):
- PATCH (1.0.x): bug fixes, no API changes
- MINOR (1.x.0): new endpoints, new optional fields — always backward compatible
- MAJOR (x.0.0): breaking changes — old version enters deprecation period

## What counts as a breaking change
The following always require a MAJOR version bump:
- Removing an endpoint
- Removing or renaming a required request field
- Removing a response field
- Changing a field's data type (string → integer)
- Changing HTTP method of an existing endpoint
- Adding a new required request field
- Changing authentication requirements

The following are NON-breaking (MINOR bump only):
- Adding a new optional request field
- Adding a new response field
- Adding a new endpoint
- Adding a new optional query parameter
- Changing error message text (not error codes)

## Deprecation timeline (minimum)
1. Announcement: deprecated version/endpoint marked in docs + Deprecation header added to all responses
2. 6-month notice period: both old and new versions active
3. Final reminder: email to all registered API consumers 30 days before sunset
4. Sunset: old version returns 410 Gone with migration instructions

## Sunset behavior
When a version is sunsetted, all its endpoints return:
HTTP 410 Gone
```json
{
  "error": "API version v1 has been sunsetted as of 2026-01-01.",
  "code": "VERSION_SUNSETTED",
  "migrate_to": "/api/v2/",
  "migration_guide": "https://yourerp.com/docs/migration/v1-to-v2",
  "sunset_date": "2026-01-01"
}
```
