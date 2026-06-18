# Schemas package initializer
from .common import PaginationSchema, PaginatedResponseSchema, ErrorSchema, ApiResponseSchema, SortSchema
from .auth import LoginSchema, LoginResponseSchema, RefreshResponseSchema, CSRFResponseSchema
from .students import StudentCreateSchema, StudentUpdateSchema, StudentResponseSchema, StudentListQuerySchema
from .attendance import AttendanceSubmitSchema, AttendanceRecordSchema, AttendanceQuerySchema, AttendanceSummarySchema
from .results import ResultUploadSchema, ResultResponseSchema, MarksheetSchema, SubjectResultSchema
from .faculty import FacultyCreateSchema, FacultyResponseSchema, LeaveRequestSchema, WorkloadSchema
from .reports import ReportGenerateSchema, ReportStatusSchema, ReportHistorySchema
from .tenant import TenantResponseSchema
