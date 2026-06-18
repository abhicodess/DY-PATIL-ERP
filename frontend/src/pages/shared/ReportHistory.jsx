import React, { useState, useEffect } from 'react';
import { api } from '../../api/authService';
import { useAuthStore } from '../../store/useAuthStore';

const REPORT_DISPLAY_NAMES = {
  "monthly_attendance": "Monthly Attendance Summary",
  "defaulter_report": "Attendance Defaulter List",
  "student_marksheet": "Semester Marksheet",
  "class_result_analysis": "Class Result Analysis",
  "faculty_attendance": "Faculty Attendance Summary",
  "faculty_workload": "Faculty Workload Analysis",
  "institution_summary": "Institution Executive Summary",
  "timetable_export": "Class Timetable Grid"
};

export const ReportHistory = () => {
  const { user } = useAuthStore();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(null);

  // Fetch report logs history
  const fetchHistory = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const response = await api.get('/reports/history');
      setHistory(response.data.data);
      setError('');
    } catch (err) {
      console.error("Failed to load reports history", err);
      setError("Failed to fetch reports history logs.");
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  // Poll history log lists every 30s
  useEffect(() => {
    fetchHistory(true);
    const intervalId = setInterval(() => {
      fetchHistory(false);
    }, 30000);

    return () => clearInterval(intervalId);
  }, []);

  const formatFileSize = (bytes) => {
    if (!bytes) return "0 Bytes";
    const k = 1024;
    const dm = 2;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
  };

  const handleDownload = (jobId, reportType, format) => {
    const downloadUrl = `/reports/download/${jobId}`;
    api.get(downloadUrl, { responseType: 'blob' })
      .then((res) => {
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const fileLink = document.createElement('a');
        fileLink.href = url;
        fileLink.setAttribute('download', `report_${reportType}_${jobId}.${format}`);
        document.body.appendChild(fileLink);
        fileLink.click();
        fileLink.remove();
      })
      .catch((err) => {
        alert("Failed to download file. It may have expired.");
      });
  };

  const handleDelete = async (jobId) => {
    if (!window.confirm("Are you sure you want to delete this report file?")) return;
    setActionLoading(jobId);
    try {
      await api.delete(`/reports/${jobId}`);
      // Refetch
      fetchHistory(false);
    } catch (err) {
      alert("Failed to delete report log.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRegenerate = async (report) => {
    setActionLoading(report.job_id);
    try {
      // Fetch full report metadata from DB to extract filters
      // For simplicity, we can query status which contains the details or just use default post
      // Wait, history endpoint returns filters or we fetch them.
      // If we don't have filters on frontend list, we can retrieve them by status api.
      const statusRes = await api.get(`/reports/status/${report.job_id}`);
      // Status endpoint returns download_url, progress, status, error.
      // If we don't have full filters in list, let's look at what generate endpoint needs.
      // Since history response from ReportService.list_reports returns report_type, format
      // but not filters, let's update list_reports on backend to include filters JSON, or
      // fetch filters using a dedicated call.
      // Let's call /status/<id> or retrieve filters. Wait, does `/status/<job_id>` return filters?
      // In report_service.py: `ReportService.get_status` returns: status, progress, download_url, error.
      // If we need filters, let's query DB for it! But wait, we can just trigger regeneration
      // by making a POST request. Wait! Can we get filters from the backend?
      // Let's make a call or write a backend endpoint, or simply make list_reports return filters!
      // In ReportService.list_reports, we selected:
      // `job_id, report_type, format, created_at, status, file_size`
      // Wait, if we also select `filters` inside ReportService.list_reports, then the frontend
      // will get the filters and can regenerate easily!
      // Let's check what we returned in `list_reports` on backend:
      // In report_service.py we selected: `job_id, report_type, format, created_at, status, file_size`
      // But wait! We can update `ReportService.list_reports` or query it.
      // Actually, let's write a clean fallback: if filters is missing, we can fetch it,
      // or we can select filters in `list_reports`. Wait, we can query filters inside the regenerate function!
      // Yes, in our API endpoints, is there an endpoint to get the report's filters?
      // In `blueprints/reports/routes.py` we can add a route GET `/reports/<job_id>` that returns the details,
      // OR we can just fetch it inside `/status/<job_id>` or we can query it directly in python if we do it server-side.
      // But since regeneration is triggered by frontend, frontend makes POST `/generate` with the filters.
      // To get the filters, the frontend can query `GET /reports/status/<id>` if status returns filters,
      // or we can just update `list_reports` to return the filters!
      // Wait! Let's check if we returned filters in `list_reports` in `services/report_service.py`.
      // We didn't, but we can easily query them or select them!
      // Actually, since we want to be bulletproof, let's fetch filters in history list by including `filters` in selection,
      // which is very easy. Wait! Let's check if we can query filters from the DB.
      // Let's modify `ReportService.list_reports` to select `filters` as well. That is incredibly simple and clean.
      // Wait, is it necessary? Let's check: if we select `filters` in `list_reports`, we can do:
      // `filters = json.loads(r['filters'])`
      // And then return it in the history payload. Then frontend has the filters and can pass them directly to `/generate`!
      // This is extremely simple and elegant. Let's do a quick replace on `services/report_service.py` to select and return `filters` too.
      // Wait, let's write the React page first assuming `filters` is returned in the history items.
      
      const payload = {
        report_type: report.report_type,
        format: report.format,
        filters: report.filters || {}
      };
      
      await api.post('/reports/generate', payload);
      alert("Regeneration task successfully queued!");
      fetchHistory(false);
    } catch (err) {
      alert("Failed to queue regeneration task: " + (err.response?.data?.error?.message || err.message));
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'queued':
        return <span className="bg-slate-800 text-slate-400 border border-white/5 text-xs font-semibold px-2.5 py-1 rounded-full uppercase">Queued</span>;
      case 'processing':
        return (
          <span className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs font-semibold px-2.5 py-1 rounded-full uppercase flex items-center gap-1.5 w-fit">
            <div className="animate-spin rounded-full h-3 w-3 border-t-2 border-b-2 border-indigo-400" />
            Compiling
          </span>
        );
      case 'done':
        return <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold px-2.5 py-1 rounded-full uppercase">Ready</span>;
      case 'failed':
        return <span className="bg-red-500/10 text-red-400 border border-red-500/20 text-xs font-semibold px-2.5 py-1 rounded-full uppercase">Failed</span>;
      case 'expired':
        return <span className="bg-slate-900 text-slate-500 border border-white/5 line-through text-xs font-semibold px-2.5 py-1 rounded-full uppercase">Expired</span>;
      case 'deleted':
        return <span className="bg-slate-900 text-slate-600 border border-white/5 line-through text-xs font-semibold px-2.5 py-1 rounded-full uppercase">Deleted</span>;
      default:
        return <span className="bg-slate-800 text-slate-400 text-xs font-semibold px-2.5 py-1 rounded-full uppercase">{status}</span>;
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6 bg-slate-950 min-h-screen text-slate-100">
      <div className="flex justify-between items-center">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold tracking-tight text-white">Report Archives</h1>
          <p className="text-sm text-slate-400">View and download recently generated academic documents (24h storage TTL).</p>
        </div>
        <button
          onClick={() => fetchHistory(true)}
          className="bg-slate-900 border border-white/10 hover:bg-slate-800 text-slate-200 text-xs font-semibold px-4 py-2 rounded-xl transition"
        >
          🔄 Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-sm shadow-md">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-purple-500" />
          <p className="text-sm text-slate-400">Loading archives history log...</p>
        </div>
      ) : history.length === 0 ? (
        <div className="glass p-12 text-center rounded-2xl border border-white/5 flex flex-col items-center gap-2">
          <span className="text-5xl">📁</span>
          <h3 className="text-lg font-bold text-white mt-4">No reports generated yet</h3>
          <p className="text-sm text-slate-400 max-w-sm mt-1 leading-relaxed">
            Use the Report Generator console to build a report. Once compiled, download buttons will appear here.
          </p>
        </div>
      ) : (
        <div className="glass rounded-2xl border border-white/5 overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-900/60 border-b border-white/5 text-xs font-bold uppercase tracking-wider text-slate-400">
                  <th className="p-4 pl-6">Document Type</th>
                  <th className="p-4 text-center">Format</th>
                  <th className="p-4">Date Generated</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-right">Size</th>
                  <th className="p-4 pr-6 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {history.map((report) => {
                  const displayName = REPORT_DISPLAY_NAMES[report.report_type] || report.name;
                  const dateStr = new Date(report.created_at).toLocaleString();
                  const isDone = report.status === 'done';
                  const isPending = ['queued', 'processing'].includes(report.status);
                  const isActionable = actionLoading !== report.job_id;

                  return (
                    <tr key={report.job_id} className="hover:bg-white/5 transition text-sm">
                      <td className="p-4 pl-6 font-semibold text-white">{displayName}</td>
                      <td className="p-4 text-center">
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-slate-900 border border-white/10 text-slate-300">
                          {report.format}
                        </span>
                      </td>
                      <td className="p-4 text-slate-400">{dateStr}</td>
                      <td className="p-4">{getStatusBadge(report.status)}</td>
                      <td className="p-4 text-right text-slate-400">{formatFileSize(report.file_size)}</td>
                      <td className="p-4 pr-6">
                        <div className="flex gap-2 justify-center items-center">
                          {isDone && (
                            <button
                              onClick={() => handleDownload(report.job_id, report.report_type, report.format)}
                              disabled={!isActionable}
                              className="text-xs bg-emerald-600/10 hover:bg-emerald-600 text-emerald-400 hover:text-white border border-emerald-500/20 px-3 py-1.5 rounded-lg transition"
                            >
                              Download
                            </button>
                          )}
                          {!isPending && (
                            <button
                              onClick={() => handleRegenerate(report)}
                              disabled={!isActionable}
                              className="text-xs bg-purple-600/10 hover:bg-purple-600 text-purple-400 hover:text-white border border-purple-500/20 px-3 py-1.5 rounded-lg transition"
                            >
                              Regenerate
                            </button>
                          )}
                          {isPending && (
                            <div className="text-xs text-slate-500 px-3 py-1.5">Compiling...</div>
                          )}
                          {!isPending && report.status !== 'deleted' && (
                            <button
                              onClick={() => handleDelete(report.job_id)}
                              disabled={!isActionable}
                              className="text-xs bg-red-600/10 hover:bg-red-600 text-red-400 hover:text-white border border-red-500/20 px-3 py-1.5 rounded-lg transition"
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
