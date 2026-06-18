import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { Calendar } from 'lucide-react';

export const ViewTimetable = () => {
  const [day, setDay] = useState('Monday');

  const { data, isLoading } = useQuery({
    queryKey: ['facultyTimetableSlots', day],
    queryFn: async () => {
      const response = await api.get('/faculty/timetable', { params: { day } });
      return response.data.data;
    },
  });

  return (
    <Layout title="My Lectures Schedule" role="faculty">
      <div className="flex flex-col gap-6">
        {/* Day Select */}
        <div className="glass p-6 rounded-2xl flex flex-wrap gap-4 items-center">
          <label className="text-sm font-semibold text-slate-300">Select Day:</label>
          <div className="flex flex-wrap gap-2">
            {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map((d) => (
              <button
                key={d}
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

        {/* Timetable Grid cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {isLoading ? (
            [1, 2].map((n) => (
              <div key={n} className="h-32 bg-slate-900 rounded-2xl animate-pulse border border-white/5" />
            ))
          ) : data?.length === 0 ? (
            <div className="col-span-3 text-center p-8 text-slate-500">
              No lecture slots assigned for {day}.
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
                  <p className="text-xs text-slate-400 mt-1">
                    Division {slot.division} • Year {slot.year} Semester {slot.semester}
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
