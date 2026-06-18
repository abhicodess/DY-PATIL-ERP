import React, { useEffect, useState, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { useAttendanceSocket } from '../../socket/attendanceSocket';

export const TakeAttendance = () => {
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [sessionData, setSessionData] = useState(null);
  const [studentsList, setStudentsList] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [saveStatus, setSaveStatus] = useState('Saved'); // Saved, Saving, Error
  const autoSaveTimerRef = useRef(null);

  // 1. Fetch today's timetable slots
  const { data: timetableData, isLoading: loadingTimetable, error: timetableError } = useQuery({
    queryKey: ['facultyTimetable'],
    queryFn: async () => {
      const response = await api.get('/faculty/timetable');
      return response.data.data;
    },
  });

  // 2. Initialize attendance session mutation
  const initSessionMutation = useMutation({
    mutationFn: async (timetableId) => {
      const response = await api.post('/attendance/session/initialize', { timetable_id: timetableId });
      return response.data.data;
    },
    onSuccess: (data) => {
      setSessionData(data);
      setStudentsList(data.students);
    },
  });

  // 3. Submit attendance (draft or final) mutation
  const submitAttendanceMutation = useMutation({
    mutationFn: async ({ records, isFinal }) => {
      const response = await api.post(`/attendance/submit?is_final=${isFinal}`, {
        session_id: sessionData?.session_id,
        records,
      });
      return response.data.data;
    },
  });

  // 4. WebSocket integration for live counts
  const socketData = useAttendanceSocket(sessionData?.session_id);

  // Sync WebSocket lock/status updates
  const sessionLocked = socketData.isLocked || sessionData?.details?.is_locked;

  // 5. Handle state toggles optimistically
  const toggleStatus = (studentId) => {
    if (sessionLocked) return;

    setStudentsList((prev) =>
      prev.map((s) => {
        if (s.id === studentId) {
          const newStatus = s.status === 'Present' ? 'Absent' : 'Present';
          return { ...s, status: newStatus };
        }
        return s;
      })
    );
    setSaveStatus('Unsaved Changes');
  };

  // 6. Auto-save every 60s
  useEffect(() => {
    if (!sessionData || sessionLocked) return;

    autoSaveTimerRef.current = setInterval(() => {
      triggerAutoSave();
    }, 60000);

    return () => {
      if (autoSaveTimerRef.current) {
        clearInterval(autoSaveTimerRef.current);
      }
    };
  }, [sessionData, studentsList, sessionLocked]);

  const triggerAutoSave = () => {
    if (sessionLocked) return;
    setSaveStatus('Saving Draft...');
    submitAttendanceMutation.mutate(
      {
        records: studentsList.map((s) => ({ student_id: s.id, status: s.status })),
        isFinal: false,
      },
      {
        onSuccess: () => setSaveStatus('Draft Saved Automatically'),
        onError: () => setSaveStatus('Auto-save Failed'),
      }
    );
  };

  const handleManualSaveDraft = () => {
    triggerAutoSave();
  };

  const handleFinalSubmit = () => {
    if (window.confirm('Are you sure you want to finalize this attendance? You cannot edit it afterwards.')) {
      setSaveStatus('Submitting...');
      submitAttendanceMutation.mutate(
        {
          records: studentsList.map((s) => ({ student_id: s.id, status: s.status })),
          isFinal: true,
        },
        {
          onSuccess: (data) => {
            setSaveStatus('Submitted & Locked');
            setSessionData((prev) => ({
              ...prev,
              details: { ...prev.details, is_locked: true },
            }));
          },
          onError: () => setSaveStatus('Failed to submit final attendance'),
        }
      );
    }
  };

  // Filter students by search input
  const filteredStudents = studentsList.filter(
    (s) =>
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.roll.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Present/Absent counts
  const presentCount = studentsList.filter((s) => s.status === 'Present').length;
  const absentCount = studentsList.length - presentCount;

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Daily Attendance Logging</h1>
        <p className="text-slate-400">Initialize and record student lectures logs here.</p>
      </header>

      {/* Grid wrapper */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Side: Timetable Slot Picker */}
        <div className="lg:col-span-1">
          <div className="glass p-6 rounded-2xl">
            <h2 className="text-xl font-semibold mb-4 text-purple-400">Today's Schedule</h2>
            
            {loadingTimetable ? (
              <div className="space-y-3">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="h-16 bg-slate-800 rounded-xl animate-pulse" />
                ))}
              </div>
            ) : timetableError ? (
              <p className="text-red-400">Failed to load timetable. Check server connection.</p>
            ) : timetableData?.length === 0 ? (
              <p className="text-slate-400">No scheduled sessions for today.</p>
            ) : (
              <div className="space-y-3">
                {timetableData?.map((slot) => (
                  <button
                    key={slot.id}
                    onClick={() => {
                      setSelectedSlot(slot);
                      initSessionMutation.mutate(slot.id);
                    }}
                    className={`w-full text-left p-4 rounded-xl transition ${
                      selectedSlot?.id === slot.id
                        ? 'bg-purple-600/30 border border-purple-500 text-white'
                        : 'bg-white/5 border border-transparent hover:bg-white/10 text-slate-300'
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-semibold text-sm">{slot.time}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                        {slot.slot_type}
                      </span>
                    </div>
                    <p className="font-bold text-base text-slate-100">{slot.subject}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Div {slot.division} • Room {slot.room}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Marking list and active sheet controls */}
        <div className="lg:col-span-2">
          {initSessionMutation.isPending ? (
            <div className="glass p-6 rounded-2xl flex flex-col items-center justify-center min-h-[300px]">
              <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-purple-500 mb-4" />
              <p className="text-slate-400">Initializing attendance list...</p>
            </div>
          ) : !sessionData ? (
            <div className="glass p-6 rounded-2xl flex items-center justify-center min-h-[300px] text-slate-400">
              Select a session from your schedule to log student attendance.
            </div>
          ) : (
            <div className="glass p-6 rounded-2xl flex flex-col gap-6">
              {/* Header stats bar */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-2xl font-bold text-white">{sessionData.details?.subject}</h2>
                    {sessionLocked ? (
                      <span className="bg-red-500/20 text-red-400 text-xs px-2 py-0.5 rounded-full font-semibold border border-red-500/30 flex items-center gap-1">
                        Locked
                      </span>
                    ) : (
                      <span className="bg-green-500/20 text-green-400 text-xs px-2 py-0.5 rounded-full font-semibold border border-green-500/30">
                        Active
                      </span>
                    )}
                  </div>
                  <p className="text-slate-400 text-sm">
                    Division {sessionData.details?.division} • Branch {sessionData.details?.branch}
                  </p>
                </div>

                <div className="flex items-center gap-4 text-sm">
                  <div className="bg-slate-900 px-3 py-2 rounded-xl border border-white/5">
                    <span className="text-green-400 font-bold text-lg">{socketData.total > 0 ? socketData.presentCount : presentCount}</span>
                    <span className="text-slate-500 text-xs block">Present</span>
                  </div>
                  <div className="bg-slate-900 px-3 py-2 rounded-xl border border-white/5">
                    <span className="text-red-400 font-bold text-lg">{socketData.total > 0 ? socketData.absentCount : absentCount}</span>
                    <span className="text-slate-500 text-xs block">Absent</span>
                  </div>
                  <div className="bg-slate-900 px-3 py-2 rounded-xl border border-white/5">
                    <span className="text-slate-300 font-bold text-lg">{socketData.total > 0 ? socketData.total : studentsList.length}</span>
                    <span className="text-slate-500 text-xs block">Total Students</span>
                  </div>
                </div>
              </div>

              {/* Status and Action Buttons */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-purple-500 animate-pulse" />
                  <span className="text-sm font-semibold text-slate-300">{saveStatus}</span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleManualSaveDraft}
                    disabled={sessionLocked}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl transition text-sm disabled:opacity-50"
                  >
                    Save Draft
                  </button>
                  <button
                    onClick={handleFinalSubmit}
                    disabled={sessionLocked}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl transition text-sm font-semibold disabled:opacity-50"
                  >
                    Submit & Lock
                  </button>
                </div>
              </div>

              {/* Search filter bar */}
              <input
                type="text"
                placeholder="Search students by name or roll..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500 text-sm"
              />

              {/* Students attendance marking cards */}
              <div className="space-y-2 max-h-[450px] overflow-y-auto pr-1">
                {filteredStudents.map((student) => (
                  <div
                    key={student.id}
                    className={`flex items-center justify-between p-3 rounded-xl border transition ${
                      student.status === 'Present'
                        ? 'bg-green-500/5 border-green-500/20'
                        : 'bg-red-500/5 border-red-500/20'
                    }`}
                  >
                    <div>
                      <h4 className="font-semibold text-slate-200 text-sm">{student.name}</h4>
                      <p className="text-xs text-slate-400">Roll: {student.roll}</p>
                    </div>

                    <button
                      onClick={() => toggleStatus(student.id)}
                      disabled={sessionLocked}
                      className={`px-4 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition ${
                        student.status === 'Present'
                          ? 'bg-green-600 hover:bg-green-700 text-white'
                          : 'bg-red-600 hover:bg-red-700 text-white'
                      } disabled:opacity-55`}
                    >
                      {student.status}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
