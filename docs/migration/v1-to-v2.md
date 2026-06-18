# Migrating from API v1 to v2

## Summary of breaking changes
| Endpoint | v1 behavior | v2 behavior |
|----------|-------------|-------------|
| GET /api/v{n}/students/list | Returns flat array | Removed — use GET /api/v2/students |
| POST /api/v{n}/auth/login | Returns { token } | Returns { access_token, refresh_token, user } |
| GET /api/v{n}/attendance | Returns snake_case | Returns camelCase (JS-friendly) |

## Step-by-step migration checklist
- [ ] Update base URL from /api/v1/ to /api/v2/
- [ ] Update login handler: token → access_token
- [ ] Replace all /students/list calls with /students
- [ ] Update field name casing in response handlers
- [ ] Test with the v2 sandbox environment first

## Parallel running period
Both v1 and v2 will be active from {announced} until {sunset}.
You can run them side by side during migration.

## Getting help
Email: api-support@yourerp.com
Docs:  https://yourerp.com/api/docs
