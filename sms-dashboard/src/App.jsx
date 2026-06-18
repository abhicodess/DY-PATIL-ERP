import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  BarChart3, 
  History, 
  Layout, 
  MessageSquare, 
  Send, 
  Settings, 
  ShieldCheck, 
  AlertCircle,
  CheckCircle2,
  Clock
} from 'lucide-react';

// --- Mock Stats Component ---
const StatCard = ({ title, value, icon: Icon, color }) => (
  <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4">
    <div className={`p-3 rounded-lg ${color}`}>
      <Icon className="w-6 h-6 white" />
    </div>
    <div>
      <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">{title}</p>
      <h3 className="text-2xl font-bold text-gray-900">{value}</h3>
    </div>
  </div>
);

// --- History Table Component ---
const HistoryTable = ({ data }) => (
  <div className="overflow-x-auto">
    <table className="w-full text-left border-collapse">
      <thead>
        <tr className="border-b border-gray-100 text-sm font-semibold text-gray-500">
          <th className="py-4 px-4">Recipient</th>
          <th className="py-4 px-4">Status</th>
          <th className="py-4 px-4">Message</th>
          <th className="py-4 px-4">Provider</th>
          <th className="py-4 px-4">Sent At</th>
        </tr>
      </thead>
      <tbody className="text-sm">
        {data.map((log) => (
          <tr key={log.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
            <td className="py-4 px-4 font-medium text-gray-700">{log.recipient}</td>
            <td className="py-4 px-4">
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium 
                ${log.status === 'delivered' ? 'bg-green-100 text-green-700' : 
                  log.status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                {log.status === 'delivered' ? <CheckCircle2 className="w-3 h-3" /> : 
                 log.status === 'failed' ? <AlertCircle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                {log.status.toUpperCase()}
              </span>
            </td>
            <td className="py-4 px-4 text-gray-500 max-w-xs truncate">{log.message}</td>
            <td className="py-4 px-4 text-gray-400 text-xs font-mono">{log.provider}</td>
            <td className="py-4 px-4 text-gray-400">{new Date(log.created_at).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

export default function SMSDashboard() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({ total: 0, delivered: 0, failed: 0, queued: 0 });

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, []);

  const fetchLogs = async () => {
    try {
      const res = await axios.get('/api/sms/history');
      setLogs(res.data);
    } catch (err) { console.error("Failed to fetch logs", err); }
  };

  const fetchStats = async () => {
    try {
      const res = await axios.get('/api/sms/analytics');
      setStats(res.data);
    } catch (err) { console.error("Failed to fetch stats", err); }
  };

  return (
    <div className="flex h-screen bg-gray-50 font-sans text-gray-900">
      {/* Sidebar */}
      <div className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-6 border-b border-slate-800 flex items-center gap-3">
          <div className="bg-blue-500 p-2 rounded-lg"><Send className="w-5 h-5 text-white" /></div>
          <span className="font-bold text-lg tracking-tight">SMS Gateway</span>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          <button onClick={() => setActiveTab('dashboard')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeTab === 'dashboard' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-400 hover:bg-slate-800'}`}>
            <Layout className="w-5 h-5" /> Dashboard
          </button>
          <button onClick={() => setActiveTab('history')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeTab === 'history' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-400 hover:bg-slate-800'}`}>
            <History className="w-5 h-5" /> SMS History
          </button>
          <button onClick={() => setActiveTab('templates')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeTab === 'templates' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-400 hover:bg-slate-800'}`}>
            <MessageSquare className="w-5 h-5" /> Templates
          </button>
          <button onClick={() => setActiveTab('parent_comm')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeTab === 'parent_comm' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-400 hover:bg-slate-800'}`}>
            <Users className="w-5 h-5" /> Parent Comm
          </button>
          <button onClick={() => setActiveTab('defaulters')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeTab === 'defaulters' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-400 hover:bg-slate-800'}`}>
            <AlertCircle className="w-5 h-5" /> Defaulters
          </button>
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-8">
          <h2 className="font-semibold text-lg text-gray-800">
            {activeTab.replace('_', ' ').charAt(0).toUpperCase() + activeTab.replace('_', ' ').slice(1)} View
          </h2>
          <div className="flex items-center gap-4">
            <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors"><Settings className="w-5 h-5" /></button>
            <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-xs">AD</div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-8">
          {activeTab === 'dashboard' && (
            <div className="space-y-8">
              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard title="Total Sent" value={stats.total} icon={BarChart3} color="bg-blue-500" />
                <StatCard title="Delivered" value={stats.delivered} icon={CheckCircle2} color="bg-emerald-500" />
                <StatCard title="Failed" value={stats.failed} icon={AlertCircle} color="bg-rose-500" />
                <StatCard title="Queued" value={stats.queued} icon={Clock} color="bg-amber-500" />
              </div>

              {/* Recent History Table */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="p-6 border-b border-gray-50 flex items-center justify-between">
                  <h3 className="font-bold text-gray-800">Recent Deliveries</h3>
                  <button onClick={fetchLogs} className="text-blue-600 text-sm font-semibold hover:underline">Refresh</button>
                </div>
                <HistoryTable data={logs.slice(0, 10)} />
              </div>
            </div>
          )}

          {activeTab === 'history' && (
             <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
               <HistoryTable data={logs} />
             </div>
          )}

          {activeTab === 'templates' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
               <div className="p-12 text-center bg-white rounded-xl border-2 border-dashed border-gray-200">
                 <p className="text-gray-400">Template Editor Coming Soon</p>
               </div>
            </div>
          )}

          {activeTab === 'parent_comm' && (
            <ParentBroadcaster />
          )}

          {activeTab === 'defaulters' && (
            <DefaulterList />
          )}
        </main>
      </div>
    </div>
  );
}
