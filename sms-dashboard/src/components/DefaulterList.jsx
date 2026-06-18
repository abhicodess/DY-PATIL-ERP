import React, { useState, useEffect } from 'react';
import { AlertTriangle, Send, Search, Filter, CheckCircle } from 'lucide-react';

const DefaulterList = () => {
  const [defaulters, setDefaulters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [threshold, setThreshold] = useState(75);
  const [department, setDepartment] = useState('');
  const [notifyStatus, setNotifyStatus] = useState(null);

  useEffect(() => {
    fetchDefaulters();
  }, [threshold, department]);

  const fetchDefaulters = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/parent/defaulters?threshold=${threshold}&department=${department}`);
      const data = await res.json();
      setDefaulters(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleNotifyAll = async () => {
    if (!window.confirm(`Are you sure you want to send SMS alerts to parents of ${defaulters.length} students?`)) return;
    
    setLoading(true);
    try {
      const res = await fetch('/api/parent/notify-defaulters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ threshold, department })
      });
      const data = await res.json();
      setNotifyStatus({ success: true, count: data.defaulters_notified });
    } catch (e) {
      setNotifyStatus({ success: false });
    }
    setLoading(false);
  };

  return (
    <div className="p-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <AlertTriangle className="text-amber-500" /> Attendance Defaulter List
          </h1>
          <p className="text-sm text-gray-500 mt-1">Identify and alert students falling below the required attendance threshold.</p>
        </div>
        
        <button 
          onClick={handleNotifyAll}
          disabled={loading || defaulters.length === 0}
          className="bg-rose-600 text-white px-6 py-2.5 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 hover:bg-rose-700 transition-all shadow-md active:scale-95 disabled:opacity-50"
        >
          <Send size={16} /> Alert All Defaulter Parents
        </button>
      </div>

      {notifyStatus && (
        <div className={`mb-6 p-4 rounded-xl flex items-center gap-3 border shadow-sm ${notifyStatus.success ? 'bg-green-50 border-green-100 text-green-700' : 'bg-red-50 border-red-100 text-red-700'}`}>
          {notifyStatus.success ? <CheckCircle size={20} /> : <AlertTriangle size={20} />}
          <span className="font-medium">
            {notifyStatus.success ? `Success: Sent ${notifyStatus.count} emergency alerts to parents.` : 'Error: Failed to process batch notifications.'}
          </span>
        </div>
      )}

      {/* FILTER BAR */}
      <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 mb-6 flex flex-wrap items-center gap-6">
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold text-gray-500 uppercase">Threshold (%)</label>
          <input 
            type="number" 
            className="w-20 bg-gray-50 border border-gray-200 rounded-lg p-2 text-sm font-bold"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
          />
        </div>
        
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold text-gray-500 uppercase">Department</label>
          <select 
            className="bg-gray-50 border border-gray-200 rounded-lg p-2 text-sm outline-none px-4"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
          >
            <option value="">All Departments</option>
            <option value="Computer Science">Computer Science</option>
            <option value="Mechanical">Mechanical</option>
            <option value="Civil">Civil</option>
          </select>
        </div>
        
        <div className="ml-auto text-sm text-gray-400 font-medium">
          Showing <span className="text-gray-900 font-bold">{defaulters.length}</span> defaulters
        </div>
      </div>

      {/* TABLE */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="py-4 px-6 text-xs font-bold text-gray-500 uppercase">Student / Roll</th>
              <th className="py-4 px-6 text-xs font-bold text-gray-500 uppercase text-center">Percentage</th>
              <th className="py-4 px-6 text-xs font-bold text-gray-500 uppercase">Stats</th>
              <th className="py-4 px-6 text-xs font-bold text-gray-500 uppercase">Department</th>
              <th className="py-4 px-6 text-xs font-bold text-gray-500 uppercase text-right">Risk Level</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
               <tr><td colSpan="5" className="py-20 text-center text-gray-400">Computing attendance analytics...</td></tr>
            ) : defaulters.length === 0 ? (
               <tr><td colSpan="5" className="py-20 text-center text-gray-400">No defaulters found for current criteria. ✅</td></tr>
            ) : defaulters.map(s => (
              <tr key={s.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="py-4 px-6">
                  <div className="font-bold text-gray-900">{s.name}</div>
                  <div className="text-xs text-blue-600 font-mono">{s.roll}</div>
                </td>
                <td className="py-4 px-6 text-center">
                  <div className={`inline-block px-3 py-1 rounded-lg text-sm font-bold shadow-sm ${s.percentage < 60 ? 'bg-red-600 text-white' : 'bg-amber-100 text-amber-700 border border-amber-200'}`}>
                    {s.percentage}%
                  </div>
                </td>
                <td className="py-4 px-6">
                  <div className="text-sm font-medium text-gray-700">Present: <span className="text-emerald-600">{s.present}</span></div>
                  <div className="text-xs text-gray-400">Total Classes: {s.total}</div>
                </td>
                <td className="py-4 px-6">
                  <span className="text-xs font-semibold bg-gray-100 px-2 py-1 rounded text-gray-600">{s.department}</span>
                </td>
                <td className="py-4 px-6 text-right">
                  {s.percentage < 60 ? (
                    <span className="text-xs font-bold text-red-600 flex items-center justify-end gap-1"><AlertTriangle size={12}/> CRITICAL</span>
                  ) : (
                    <span className="text-xs font-bold text-amber-500">AT RISK</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DefaulterList;
