import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { useAuth } from '../../context/AuthContext';
import { Calendar } from 'lucide-react';

export const MyTimetable = () => {
  const { user } = useAuth();
  const [day, setDay] = useState('Monday');

  // Fetch timetable slots for student cohort
  const { data, isLoading, error } = useQuery({
    queryKey: ['studentTimetableSlots', day, user?.department, user?.division, user?.year],
    queryFn: async () => {
      // If we don't have user cohort, wait
      if (!user) return [];
      const response = await api.get('/timetable', {
        params: {
          day,
          branch: user.department,
          division: user.division,
          year: user.year,
          per_page: 50,
        },
      });
      return response.data.data;
    },
    enabled: !!user,
  });

  return (
    <Layout title="My Class Schedule" role="student">
      <div className="flex flex-col gap-6">
        {/* Day Select */}
        <div className="glass p-6 rounded-2xl flex flex-wrap gap-4 items-center">
          <label className="text-sm font-semibold text-slate-300">Select Day:</label>
          <div className="flex flex-wrap gap-2">
            {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map((d) => (
              <button
                onClick={() => setDay(d)}
                className={`px-4 py-2 rounded-xl text-xs font-bold capitalize transition ${
                  day === d
                    ? 'bg-purple-600 text-white'
                    : 'bg-white/5 text-slate-400 hover:text-slate-200'
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        {/* Timetable Grid Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {isLoading ? (
            [1, 2].map((n) => (
              <div key={n} className="h-32 bg-slate-900 rounded-2xl animate-pulse border border-white/5" />
            ))
          ) : error ? (
            <div className="col-span-3 bg-red-500/10 border border-red-500/20 text-red-400 p-6 rounded-2xl">
              Failed to load timetable slots.
            </div>
          ) : data?.length === 0 ? (
            <div className="col-span-3 text-center p-8 text-slate-500">
              No classes scheduled for {day}.
            </div>
          ) : (
            data?.map((slot) => (
              <div key={slot.id} className="glass p-6 rounded-2xl flex flex-col gap-3 relative overflow-hidden">
                <div className="flex justify-between items-center">
                  <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-white/5 font-semibold">
                    {slot.slot_type}
                  </span>
                  <span className="text-slate-400 font-semibold text-xs flex items-center gap-1">
                    Room {slot.room}
                  </span>
                </div>
                <div>
                  <h4 className="text-lg font-bold text-white leading-tight">{slot.subject}</h4>
                  <p className="text-sm text-slate-300 mt-1">Instructor: {slot.teacher || 'N/A'}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    Cohort {slot.year} - {slot.division} ({slot.branch})
                  </p>
                </div>
                <div className="border-t border-white/5 pt-3 flex items-center justify-between text-xs text-purple-400 font-semibold">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    {slot.time}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </Layout>
  );
};
