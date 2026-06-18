import React, { useState, useEffect } from 'react';
import { Megaphone, Users, ShieldCheck, Send, Info, Filter } from 'lucide-react';

const ParentBroadcaster = () => {
  const [dept, setDept] = useState('Computer Science');
  const [template, setTemplate] = useState('absent_alert');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);

  const departments = ['Computer Science', 'Mechanical', 'Civil', 'Electronics'];
  
  const handleBroadcast = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/parent/broadcast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
           department: dept,
           template_slug: template,
           context: { date: new Date().toLocaleDateString() }
        })
      });
      const data = await res.json();
      setStatus({ type: 'success', msg: `Broadcast initiated to ${data.processed_count} parents.` });
    } catch (e) {
      setStatus({ type: 'error', msg: 'Failed to initiate broadcast.' });
    }
    setLoading(false);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Megaphone className="text-blue-600" /> Parent Communication Center
          </h1>
          <p className="text-sm text-gray-500 mt-1">Broadcast announcements to guardians and parents instantly.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* CONFIG PANEL */}
        <div className="md:col-span-2 space-y-6">
          <div className="bg-white rounded-xl border border-gray-100 p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <Filter size={16} /> Broadcast Configuration
            </h3>
            
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Target Department</label>
                <select 
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2.5 text-sm outline-none focus:border-blue-500"
                  value={dept}
                  onChange={(e) => setDept(e.target.value)}
                >
                  {departments.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Message Template</label>
                <select 
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2.5 text-sm outline-none focus:border-blue-500"
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                >
                  <option value="absent_alert">Student Absent Alert</option>
                  <option value="fee_reminder">Fee Due Reminder</option>
                  <option value="holiday_notice">Holiday Announcement</option>
                </select>
              </div>
            </div>

            <div className="bg-blue-50 rounded-lg p-4 border border-blue-100">
              <div className="flex gap-3">
                <Info className="text-blue-600 shrink-0" size={18} />
                <div className="text-sm text-blue-800">
                  <strong>Preview:</strong> "Dear Parent, [Student Name] was marked absent on {new Date().toLocaleDateString()}. Please contact administration for any queries."
                </div>
              </div>
            </div>

            <button 
              onClick={handleBroadcast}
              disabled={loading}
              className="mt-6 w-full bg-slate-900 text-white rounded-lg py-3 font-semibold text-sm flex items-center justify-center gap-2 hover:bg-blue-600 transition-colors disabled:opacity-50"
            >
              {loading ? 'Processing...' : <><Send size={16} /> Launch Broadcast</>}
            </button>
            
            {status && (
              <div className={`mt-4 p-3 rounded-lg text-sm ${status.type === 'success' ? 'bg-green-50 text-green-700 border border-green-100' : 'bg-red-50 text-red-700 border border-red-100'}`}>
                {status.msg}
              </div>
            )}
          </div>
        </div>

        {/* STATS PANEL */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-blue-50 rounded-lg text-blue-600"><Users size={20} /></div>
              <div className="text-xs font-bold text-gray-400 uppercase">Total Parent Contacts</div>
            </div>
            <div className="text-2xl font-bold">1,840</div>
          </div>
          
          <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-emerald-50 rounded-lg text-emerald-600"><ShieldCheck size={20} /></div>
              <div className="text-xs font-bold text-gray-400 uppercase">Primary Guardians</div>
            </div>
            <div className="text-2xl font-bold">1,240</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ParentBroadcaster;
