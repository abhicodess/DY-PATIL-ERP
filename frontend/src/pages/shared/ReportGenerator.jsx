import React, { useState, useEffect } from 'react';
import { api } from '../../api/authService';
import { useAuthStore } from '../../store/useAuthStore';

// Static Registry mapping to flask-side REPORT_REGISTRY definitions
const FRONTEND_REPORT_REGISTRY = {
  "monthly_attendance": {
    "name": "Monthly Attendance Summary",
    "description": "Monthly attendance summary with class averages, percentage indicators, and visualization.",
    "allowed_roles": ["admin", "faculty"],
    "required_filters": ["department", "month", "academic_year"],
    "optional_filters": ["year", "division"],
    "formats": ["pdf", "xlsx"],
    "estimated_seconds": 30
  },
  "defaulter_report": {
    "name": "Attendance Defaulter List",
    "description": "Urgent alert list of students falling below a threshold, grouped by department.",
    "allowed_roles": ["admin", "faculty"],
    "required_filters": ["department", "as_of_date"],
    "optional_filters": ["year", "threshold"],
    "formats": ["pdf", "xlsx"],
    "estimated_seconds": 20
  },
  "student_marksheet": {
    "name": "Semester Marksheet",
    "description": "Student marksheet containing grades, SGPA, and a verification QR code.",
    "allowed_roles": ["admin", "student"],
    "required_filters": ["student_id", "semester"],
    "optional_filters": [],
    "formats": ["pdf"],
    "estimated_seconds": 10
  },
  "class_result_analysis": {
    "name": "Class Result Analysis",
    "description": "Complex class performance breakdown with donut charts and subject-wise averages.",
    "allowed_roles": ["admin", "faculty"],
    "required_filters": ["department", "year", "semester"],
    "optional_filters": ["division"],
    "formats": ["pdf"],
    "estimated_seconds": 45
  },
  "faculty_attendance": {
    "name": "Faculty Attendance Summary",
    "description": "Working days and attendance percentages for department faculty members.",
    "allowed_roles": ["admin"],
    "required_filters": ["month", "academic_year"],
    "optional_filters": ["department"],
    "formats": ["pdf", "xlsx"],
    "estimated_seconds": 15
  },
  "faculty_workload": {
    "name": "Faculty Workload Analysis",
    "description": "Timetable loads, lectures scheduled versus lectures taken.",
    "allowed_roles": ["admin"],
    "required_filters": ["semester", "academic_year"],
    "optional_filters": ["department"],
    "formats": ["pdf", "xlsx"],
    "estimated_seconds": 20
  },
  "institution_summary": {
    "name": "Institution Executive Summary",
    "description": "High-level summary of enrollments, attendance, and results across all departments.",
    "allowed_roles": ["admin"],
    "required_filters": ["academic_year", "as_of_date"],
    "optional_filters": [],
    "formats": ["pdf"],
    "estimated_seconds": 60
  },
  "timetable_export": {
    "name": "Class Timetable Grid",
    "description": "Weekly timetable grid formatted for a specific division and semester.",
    "allowed_roles": ["admin", "faculty", "student"],
    "required_filters": ["department", "year", "division", "semester"],
    "optional_filters": [],
    "formats": ["pdf"],
    "estimated_seconds": 15
  }
};

const DEPARTMENTS = ["IT", "CS", "MECH", "CIVIL", "EXTC", "AIDS"];
const DIVISIONS = ["A", "B", "C", "D"];
const YEARS = ["I", "II", "III", "IV"];
const SEMESTERS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"];
const MONTHS = [
  { value: "1", label: "January" },
  { value: "2", label: "February" },
  { value: "3", label: "March" },
  { value: "4", label: "April" },
  { value: "5", label: "May" },
  { value: "6", label: "June" },
  { value: "7", label: "July" },
  { value: "8", label: "August" },
  { value: "9", label: "September" },
  { value: "10", label: "October" },
  { value: "11", label: "November" },
  { value: "12", label: "December" }
];

export const ReportGenerator = () => {
  const { user } = useAuthStore();
  const userRole = user?.role || 'student';

  const [selectedType, setSelectedType] = useState(null);
  const [selectedFormat, setSelectedFormat] = useState('pdf');
  const [filters, setFilters] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Job progress tracking state
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  const [estRemaining, setEstRemaining] = useState(null);

  // Poll status interval
  useEffect(() => {
    let intervalId = null;
    if (jobId && ['queued', 'processing'].includes(jobStatus)) {
      intervalId = setInterval(async () => {
        try {
          const response = await api.get(`/reports/status/${jobId}`);
          const statusData = response.data.data;
          setJobStatus(statusData.status);
          setProgress(statusData.progress);
          
          if (statusData.status === 'done') {
            clearInterval(intervalId);
          } else if (statusData.status === 'failed') {
            setError(statusData.error || 'Report generation failed.');
            clearInterval(intervalId);
          }
        } catch (pollErr) {
          console.error("Failed to poll report job status", pollErr);
        }
      }, 3000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [jobId, jobStatus]);

  // Countdown timer for estimated duration
  useEffect(() => {
    let timerId = null;
    if (estRemaining !== null && estRemaining > 0 && ['queued', 'processing'].includes(jobStatus)) {
      timerId = setInterval(() => {
        setEstRemaining((prev) => (prev > 1 ? prev - 1 : 0));
      }, 1000);
    }
    return () => {
      if (timerId) clearInterval(timerId);
    };
  }, [estRemaining, jobStatus]);

  // Populate dynamic default filters
  const handleSelectReport = (type) => {
    setSelectedType(type);
    setSelectedFormat(FRONTEND_REPORT_REGISTRY[type].formats[0]);
    setError('');
    
    // Set role constraints defaults
    const defaultFilters = {};
    if (type === 'student_marksheet' && userRole === 'student') {
      defaultFilters['student_id'] = user.id;
    }
    if (userRole === 'student' && user.department) {
      defaultFilters['department'] = user.department;
    }
    if (userRole === 'faculty' && user.department) {
      defaultFilters['department'] = user.department;
    }
    if (FRONTEND_REPORT_REGISTRY[type].required_filters.includes('as_of_date')) {
      defaultFilters['as_of_date'] = new Date().toISOString().split('T')[0];
    }
    if (FRONTEND_REPORT_REGISTRY[type].required_filters.includes('academic_year')) {
      defaultFilters['academic_year'] = '2025-26';
    }
    if (FRONTEND_REPORT_REGISTRY[type].optional_filters.includes('threshold')) {
      defaultFilters['threshold'] = 75;
    }
    setFilters(defaultFilters);
    setJobId(null);
    setJobStatus(null);
  };

  const handleFilterChange = (key, val) => {
    setFilters((prev) => ({ ...prev, [key]: val }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    setJobId(null);
    setJobStatus('queued');
    setProgress(0);
    setEstRemaining(FRONTEND_REPORT_REGISTRY[selectedType].estimated_seconds);

    try {
      const response = await api.post('/reports/generate', {
        report_type: selectedType,
        format: selectedFormat,
        filters
      });
      const data = response.data.data;
      setJobId(data.job_id);
      setJobStatus(data.status);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to submit report request.');
      setJobStatus(null);
    } finally {
      setLoading(false);
    }
  };

  const downloadFile = () => {
    // Standard secure download streaming URL
    const downloadUrl = `/api/v1/reports/download/${jobId}`;
    const token = useAuthStore.getState().accessToken;
    
    // Perform redirection to trigger browser download
    const link = document.createElement('a');
    link.href = downloadUrl + `?token=${token}`; // Wait, weasyprint fallback or direct streaming
    // Or open in new window with access token embedded or since it's GET download we stream it.
    // Flask endpoint requires JWT. If it's sent as a standard GET, we can fetch it as a blob and save it:
    api.get(downloadUrl, { responseType: 'blob' })
      .then((res) => {
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const fileLink = document.createElement('a');
        fileLink.href = url;
        fileLink.setAttribute('download', `report_${selectedType}_${jobId}.${selectedFormat}`);
        document.body.appendChild(fileLink);
        fileLink.click();
        fileLink.remove();
      })
      .catch((err) => {
        setError("Download failed. File might have expired.");
      });
  };

  // Filter registry types based on user role
  const visibleReports = Object.keys(FRONTEND_REPORT_REGISTRY).filter((key) =>
    FRONTEND_REPORT_REGISTRY[key].allowed_roles.includes(userRole)
  );

  return (
    <div className="flex flex-col gap-6 p-6 bg-slate-950 min-h-screen text-slate-100">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-white">Academic Reporting Hub</h1>
        <p className="text-sm text-slate-400">Generate on-demand, university-branded PDF and Excel reports asynchronously.</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-sm shadow-md">
          {error}
        </div>
      )}

      {/* STEP 1: REPORT SELECTOR CARD GRID */}
      {!selectedType && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {visibleReports.map((key) => {
            const r = FRONTEND_REPORT_REGISTRY[key];
            return (
              <div
                key={key}
                onClick={() => handleSelectReport(key)}
                className="glass p-6 rounded-2xl border border-white/5 hover:border-purple-500/40 hover:scale-[1.02] cursor-pointer transition flex flex-col justify-between gap-4 relative overflow-hidden group shadow-lg"
              >
                <div className="absolute -top-10 -right-10 w-24 h-24 bg-purple-600/10 rounded-full blur-2xl group-hover:bg-purple-600/20 transition" />
                <div className="flex flex-col gap-2">
                  <h3 className="text-lg font-bold text-white group-hover:text-purple-400 transition">{r.name}</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">{r.description}</p>
                </div>
                <div className="flex items-center justify-between mt-2 pt-4 border-t border-white/5">
                  <div className="flex gap-1.5">
                    {r.formats.map((f) => (
                      <span key={f} className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-slate-900 border border-white/10 text-slate-300">
                        {f}
                      </span>
                    ))}
                  </div>
                  <span className="text-[10px] text-slate-400 italic">Est: ~{r.estimated_seconds}s</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* STEP 2: REPORT FILTERS & GENERATION CONSOLE */}
      {selectedType && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Controls form */}
          <div className="lg:col-span-2 glass p-6 rounded-2xl border border-white/5 shadow-xl flex flex-col gap-6">
            <div className="flex justify-between items-center pb-4 border-b border-white/5">
              <h2 className="text-xl font-semibold text-white">{FRONTEND_REPORT_REGISTRY[selectedType].name}</h2>
              <button
                onClick={() => setSelectedType(null)}
                className="text-xs text-slate-400 hover:text-white transition uppercase tracking-wider font-semibold"
              >
                &larr; Change Report
              </button>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Format selection */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-400 uppercase">Export Format</label>
                  <select
                    value={selectedFormat}
                    onChange={(e) => setSelectedFormat(e.target.value)}
                    className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-purple-500"
                  >
                    {FRONTEND_REPORT_REGISTRY[selectedType].formats.map((f) => (
                      <option key={f} value={f}>{f.toUpperCase()}</option>
                    ))}
                  </select>
                </div>

                {/* DRAFT Checkbox */}
                <div className="flex items-center gap-2 mt-6">
                  <input
                    type="checkbox"
                    id="is_draft"
                    checked={filters['is_draft'] || false}
                    onChange={(e) => handleFilterChange('is_draft', e.target.checked)}
                    className="w-4 h-4 rounded accent-purple-600 focus:ring-0 cursor-pointer"
                  />
                  <label htmlFor="is_draft" className="text-xs font-semibold text-slate-400 uppercase cursor-pointer">
                    Apply DRAFT Watermark
                  </label>
                </div>

                {/* Render required dynamic inputs */}
                {FRONTEND_REPORT_REGISTRY[selectedType].required_filters.map((f) => {
                  if (f === 'department') {
                    const isStudentOrFaculty = ['student', 'faculty'].includes(userRole);
                    return (
                      <div key={f} className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase">Department</label>
                        <select
                          value={filters[f] || ''}
                          required
                          disabled={isStudentOrFaculty && !!user.department}
                          onChange={(e) => handleFilterChange(f, e.target.value)}
                          className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-purple-500 disabled:opacity-60"
                        >
                          <option value="">Select Department</option>
                          {DEPARTMENTS.map((d) => (
                            <option key={d} value={d}>{d}</option>
                          ))}
                        </select>
                      </div>
                    );
                  }

                  if (f === 'month') {
                    return (
                      <div key={f} className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase">Month</label>
                        <select
                          value={filters[f] || ''}
                          required
                          onChange={(e) => handleFilterChange(f, e.target.value)}
                          className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-purple-500"
                        >
                          <option value="">Select Month</option>
                          {MONTHS.map((m) => (
                            <option key={m.value} value={m.value}>{m.label}</option>
                          ))}
                        </select>
                      </div>
                    );
                  }

                  if (f === 'student_id') {
                    const isSelf = userRole === 'student';
                    return (
                      <div key={f} className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase">Student ID / Roll Reference</label>
                        <input
                          type="number"
                          required
                          disabled={isSelf}
                          value={filters[f] || ''}
                          onChange={(e) => handleFilterChange(f, e.target.value)}
                          placeholder="e.g. 15"
                          className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-purple-500 disabled:opacity-60"
                        />
                      </div>
                    );
                  }

                  if (f === 'semester') {
                    return (
                      <div key={f} className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase">Semester</label>
                        <select
                          value={filters[f] || ''}
                          required
                          onChange={(e) => handleFilterChange(f, e.target.value)}
                          className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-purple-500"
                        >
                          <option value="">Select Semester</option>
                          {SEMESTERS.map((s) => (
                            <option key={s} value={s}>Semester {s}</option>
                          ))}
                        </select>
                      </div>
                    );
                  }

                  if (f === 'as_of_date') {
                    return (
                      <div key={f} className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase">As of Date</label>
                        <input
                          type="date"
                          required
                          value={filters[f] || ''}
                          onChange={(e) => handleFilterChange(f, e.target.value)}
                          className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-purple-500"
                        />
                      </div>
                    );
                  }

                  return (
                    <div key={f} className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-slate-400 uppercase">{f.replace('_', ' ')}</label>
                      <input
                        type="text"
                        required
                        value={filters[f] || ''}
                        onChange={(e) => handleFilterChange(f, e.target.value)}
                        placeholder={`Enter ${f}`}
                        className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-purple-500"
                      />
                    </div>
                  );
                })}

                {/* Render optional dynamic inputs */}
                {FRONTEND_REPORT_REGISTRY[selectedType].optional_filters.map((f) => {
                  if (f === 'year') {
                    return (
                      <div key={f} className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase">Year (Optional)</label>
                        <select
                          value={filters[f] || ''}
                          onChange={(e) => handleFilterChange(f, e.target.value)}
                          className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-purple-500"
                        >
                          <option value="">All Years</option>
                          {YEARS.map((y) => (
                            <option key={y} value={y}>Year {y}</option>
                          ))}
                        </select>
                      </div>
                    );
                  }

                  if (f === 'division') {
                    return (
                      <div key={f} className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase">Division (Optional)</label>
                        <select
                          value={filters[f] || ''}
                          onChange={(e) => handleFilterChange(f, e.target.value)}
                          className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-purple-500"
                        >
                          <option value="">All Divisions</option>
                          {DIVISIONS.map((d) => (
                            <option key={d} value={d}>Division {d}</option>
                          ))}
                        </select>
                      </div>
                    );
                  }

                  if (f === 'threshold') {
                    return (
                      <div key={f} className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase">Threshold % (Optional)</label>
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={filters[f] || ''}
                          onChange={(e) => handleFilterChange(f, parseInt(e.target.value) || '')}
                          placeholder="e.g. 75"
                          className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-purple-500"
                        />
                      </div>
                    );
                  }

                  return null;
                })}
              </div>

              <button
                type="submit"
                disabled={loading || ['queued', 'processing'].includes(jobStatus)}
                className="bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 px-6 rounded-xl transition shadow-lg shadow-purple-600/20 disabled:opacity-50 mt-4 self-start"
              >
                {loading ? 'Submitting request...' : 'Compile Document'}
              </button>
            </form>
          </div>

          {/* PROGRESS CONTAINER */}
          <div className="glass p-6 rounded-2xl border border-white/5 flex flex-col gap-6 justify-center shadow-xl h-fit">
            <h3 className="text-md font-bold text-white pb-3 border-b border-white/5">Compilation Status</h3>
            
            {!jobStatus && (
              <div className="text-center py-10 flex flex-col items-center gap-2">
                <span className="text-4xl">📊</span>
                <p className="text-sm text-slate-400">Select parameters and trigger compile to initialize.</p>
              </div>
            )}

            {jobStatus && (
              <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-bold uppercase tracking-wider text-purple-400">
                    Status: {jobStatus}
                  </span>
                  {['queued', 'processing'].includes(jobStatus) && (
                    <span className="text-xs text-slate-400 animate-pulse">Running...</span>
                  )}
                </div>

                {/* Progress bar */}
                <div className="w-full bg-slate-900 rounded-full h-3.5 border border-white/5 overflow-hidden">
                  <div
                    className="bg-purple-600 h-full transition-all duration-500 rounded-full"
                    style={{ width: `${progress}%` }}
                  />
                </div>

                <div className="flex justify-between text-xs text-slate-400">
                  <span>{progress}% Completed</span>
                  {estRemaining !== null && estRemaining > 0 && (
                    <span>Est: ~{estRemaining}s remaining</span>
                  )}
                </div>

                {jobStatus === 'done' && (
                  <div className="flex flex-col gap-2 mt-4">
                    <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded-xl text-center">
                      Report successfully compiled!
                    </div>
                    <button
                      onClick={downloadFile}
                      className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2.5 rounded-xl transition flex items-center justify-center gap-2 mt-2 shadow-lg shadow-emerald-600/20"
                    >
                      💾 Download Report
                    </button>
                  </div>
                )}

                {jobStatus === 'failed' && (
                  <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-xl text-center">
                    Compilation failed. Please try again.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
