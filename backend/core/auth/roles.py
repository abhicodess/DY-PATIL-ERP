# backend/core/auth/roles.py

class Roles:
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    HOD = "hod"
    FACULTY = "faculty"
    STUDENT = "student"
    PARENT = "parent"

class Permissions:
    ATTENDANCE_CREATE = "attendance.create"
    ATTENDANCE_EDIT = "attendance.edit"
    ATTENDANCE_LOCK = "attendance.lock"
    ATTENDANCE_OVERRIDE = "attendance.override"
    TIMETABLE_MANAGE = "timetable.manage"
    ANALYTICS_VIEW = "analytics.view"
    REPORTS_EXPORT = "reports.export"

# Role-to-Permission mapping for RBAC enforcement
ROLE_PERMISSIONS = {
    Roles.SUPER_ADMIN: [
        Permissions.ATTENDANCE_CREATE, Permissions.ATTENDANCE_EDIT, Permissions.ATTENDANCE_LOCK, 
        Permissions.ATTENDANCE_OVERRIDE, Permissions.TIMETABLE_MANAGE, Permissions.ANALYTICS_VIEW, 
        Permissions.REPORTS_EXPORT
    ],
    Roles.ADMIN: [
        Permissions.ATTENDANCE_CREATE, Permissions.ATTENDANCE_EDIT, Permissions.ATTENDANCE_LOCK, 
        Permissions.TIMETABLE_MANAGE, Permissions.ANALYTICS_VIEW, Permissions.REPORTS_EXPORT
    ],
    Roles.HOD: [
        Permissions.ATTENDANCE_CREATE, Permissions.ATTENDANCE_EDIT, Permissions.ATTENDANCE_LOCK,
        Permissions.ANALYTICS_VIEW, Permissions.REPORTS_EXPORT
    ],
    Roles.FACULTY: [
        Permissions.ATTENDANCE_CREATE, Permissions.ATTENDANCE_EDIT, Permissions.ANALYTICS_VIEW
    ],
    Roles.STUDENT: [
        Permissions.ANALYTICS_VIEW # Can only view their own analytics
    ],
    Roles.PARENT: [
        Permissions.ANALYTICS_VIEW # Can only view their child's analytics
    ]
}
