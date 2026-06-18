import React, { useState, useEffect, useMemo, useReducer, createContext, useContext } from 'react';
import { 
  LayoutDashboard, 
  UserCheck, 
  Users, 
  BarChart3, 
  Bell, 
  Settings, 
  LogOut, 
  Search, 
  Filter, 
  ChevronRight, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Calendar as CalendarIcon,
  AlertCircle,
  MoreVertical,
  Download,
  FileText,
  UserPlus,
  BookOpen,
  Mail,
  Smartphone,
  Moon,
  Sun,
  Menu,
  X
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip, 
  ResponsiveContainer, 
  LineChart, 
  Line,
  Cell,
  PieChart,
  Pie
} from 'recharts';

/**
 * ━━━ MOCK DATA ━━━
 */

const MOCK_FACULTY = {
  id: 'fac_101',
  name: 'Dr. Priya Sharma',
  email: 'priya.sharma@dypatil.edu',
  dept: 'Computer Science',
  role: 'Faculty',
  avatar: 'PS'
};

const SUBJECTS = [
  { id: 'CS301', name: 'Data Structures', batch: 'CS-2023-A', section: 'III-A' },
  { id: 'CS302', name: 'DBMS', batch: 'CS-2023-A', section: 'III-A' },
  { id: 'CS303', name: 'Operating Systems', batch: 'CS-2023-B', section: 'III-B' }
];

const GENERATE_STUDENTS = (prefix, count) => {
  const names = [
    'Aarav Patel', 'Ishani Gupta', 'Rohan Mehra', 'Sanya Iyer', 'Vikram Singh',
    'Ananya Reddy', 'Arjun Verma', 'Kavya Nair', 'Rishi Kapoor', 'Meera Deshmukh',
    'Aditya Joshi', 'Zoya Khan', 'Sameer Malhotra', 'Diya Sharma', 'Varun Rao',
    'Neha Patil', 'Kabir Bansal', 'Siddharth Jain', 'Priya Mani', 'Rahul Bose',
    'Tanvi Hegde', 'Abhishek Das', 'Sneha Kulkarni', 'Pranav Sawant', 'Anjali Thakur',
    'Yash Vardhan', 'Isha Shrivastav', 'Manish Pandey', 'Ritu Grewal', 'Deepak More'
  ];
  return Array.from({ length: count }, (_, i) => ({
    id: `${prefix}${23001 + i}`,
    roll: `${prefix}${23001 + i}`,
    name: names[i % names.length],
    batch: prefix.includes('A') ? 'CS-2023-A' : 'CS-2023-B',
    attendance: Math.floor(Math.random() * (100 - 45) + 45), // 45% to 100%
    status: 'Present'
  }));
};

const STUDENTS_A = GENERATE_STUDENTS('CS', 30);
const STUDENTS_B = GENERATE_STUDENTS('CS', 28);

const INITIAL_STATE = {
  user: JSON.parse(localStorage.getItem('faculty_user')) || null,
  isAuthenticated: !!localStorage.getItem('faculty_user'),
  darkMode: localStorage.getItem('darkMode') === 'true',
  notifications: [
    { id: 1, type: 'alert', message: 'Rohan Mehra is below 75% attendance.', read: false, time: '2h ago' },
    { id: 2, type: 'leave', message: 'Sanya Iyer submitted a medical leave request.', read: false, time: '5h ago' },
    { id: 3, type: 'info', message: 'Quiz 2 attendance marks synchronized.', read: true, time: 'Yesterday' }
  ],
  attendanceRecords: JSON.parse(localStorage.getItem('attendance_records')) || [],
  selectedSubject: null,
  selectedDate: new Date().toISOString().split('T')[0],
  threshold: 75
};

/**
 * ━━━ UI DESIGN SYSTEM / CSS ━━━
 */

const CSS_VARIABLES = `
  :root {
    --primary: #6366F1;
    --primary-light: rgba(99, 102, 241, 0.1);
    --bg: #F8F9FC;
    --card-bg: #FFFFFF;
    --sidebar-bg: #FFFFFF;
    --sidebar-text: #6B7280;
    --sidebar-active: #6366F1;
    --sidebar-active-bg: #F5F3FF;
    --text-primary: #111827;
    --text-secondary: #6B7280;
    --text-muted: #9CA3AF;
    --border: #E5E7EB;
    --success: #10B981;
    --success-bg: rgba(16, 185, 129, 0.15);
    --warning: #F59E0B;
    --warning-bg: rgba(245, 158, 11, 0.15);
    --danger: #EF4444;
    --danger-bg: rgba(239, 68, 68, 0.15);
    --info: #3B82F6;
    --info-bg: rgba(59, 130, 246, 0.15);
    --radius: 12px;
    --transition: 150ms ease;
  }

  .dark {
    --bg: #0F0F13;
    --card-bg: #1A1A24;
    --sidebar-bg: #1A1A24;
    --sidebar-text: #9CA3AF;
    --text-primary: #F3F4F6;
    --text-secondary: #9CA3AF;
    --text-muted: #6B7280;
    --border: #2D2D3D;
    --sidebar-active-bg: rgba(99, 102, 241, 0.1);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text-primary); transition: background var(--transition), color var(--transition); }
  
  .app-container { display: flex; min-height: 100vh; overflow: hidden; }
  
  /* Sidebar */
  .sidebar { width: 240px; background: var(--sidebar-bg); border-right: 1px solid var(--border); display: flex; flex-direction: column; height: 100vh; position: fixed; z-index: 100; transition: transform var(--transition); }
  .sidebar-header { padding: 32px 24px; display: flex; align-items: center; gap: 12px; }
  .logo-box { width: 32px; height: 32px; background: var(--primary); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; }
  .logo-text { font-size: 18px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }
  .nav-group { flex: 1; padding: 0 12px; }
  .nav-label { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; padding: 24px 12px 8px; }
  .nav-item { display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: 8px; color: var(--sidebar-text); cursor: pointer; transition: var(--transition); font-size: 14px; font-weight: 500; text-decoration: none; border-left: 3px solid transparent; }
  .nav-item:hover { background: var(--bg); color: var(--text-primary); }
  .nav-item.active { background: var(--sidebar-active-bg); color: var(--sidebar-active); border-left-color: var(--sidebar-active); }
  
  /* Main Content Area */
  .main-content { flex: 1; margin-left: 240px; display: flex; flex-direction: column; min-height: 100vh; position: relative; }
  .header { height: 72px; padding: 0 40px; background: var(--card-bg); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 90; }
  .page-title { font-size: 20px; font-weight: 600; color: var(--text-primary); }
  .header-actions { display: flex; align-items: center; gap: 20px; }
  .icon-btn { width: 40px; height: 40px; border-radius: 10px; border: 1px solid var(--border); background: transparent; color: var(--text-secondary); display: flex; align-items: center; justify-content: center; position: relative; }
  .icon-btn:hover { background: var(--bg); color: var(--primary); }
  .badge-dot { position: absolute; top: 8px; right: 8px; width: 8px; height: 8px; background: var(--danger); border-radius: 50%; border: 2px solid var(--card-bg); }
  
  .user-profile { display: flex; align-items: center; gap: 12px; padding-left: 20px; border-left: 1px solid var(--border); }
  .avatar { width: 36px; height: 36px; border-radius: 10px; background: #6366F1; color: white; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; }
  .user-info { display: flex; flex-direction: column; }
  .user-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
  .user-role { font-size: 12px; color: var(--text-muted); }

  .content-area { padding: 40px; max-width: 1200px; width: 100%; margin: 0 auto; flex: 1; }

  /* Dashboard Cards */
  .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; margin-bottom: 32px; }
  .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; }
  .stat-label { font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 4px; }
  .stat-value { font-size: 28px; font-weight: 700; color: var(--text-primary); }
  .stat-trend { font-size: 12px; margin-top: 8px; display: flex; align-items: center; gap: 4px; }
  .trend-up { color: var(--success); }
  .trend-down { color: var(--danger); }

  /* Buttons */
  .button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; height: 44px; padding: 0 20px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all var(--transition); border: 1px solid transparent; }
  .btn-primary { background: var(--primary); color: white; }
  .btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
  .btn-ghost { background: transparent; border-color: var(--border); color: var(--text-secondary); }
  .btn-ghost:hover { background: var(--bg); color: var(--text-primary); }
  .btn-danger { background: var(--danger); color: white; }

  /* Forms Control */
  .selection-bar { background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px 24px; margin-bottom: 24px; display: flex; gap: 24px; align-items: center; }
  .input-group { flex: 1; }
  .input-label { font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px; display: block; }
  .select { width: 100%; height: 40px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg); padding: 0 12px; font-size: 14px; outline: none; }
  .select:focus { border-color: var(--primary); }

  /* Professional Roster Display */
  .roster-table { width: 100%; border-collapse: collapse; margin-top: 12px; }
  .roster-header th { padding: 16px; text-align: left; font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; border-bottom: 1px solid var(--border); }
  .roster-row { border-bottom: 1px solid var(--border); transition: background var(--transition); }
  .roster-row:hover { background: var(--bg); }
  .roster-row td { padding: 16px; font-size: 14px; color: var(--text-primary); }
  
  .status-toggle { display: flex; background: var(--bg); border-radius: 10px; padding: 4px; gap: 4px; }
  .toggle-btn { height: 32px; padding: 0 12px; border-radius: 6px; border: none; font-size: 12px; font-weight: 700; color: var(--text-muted); background: transparent; cursor: pointer; transition: all 150ms; }
  .toggle-btn.active.P { background: var(--success); color: white; }
  .toggle-btn.active.A { background: var(--danger); color: white; }
  .toggle-btn.active.L { background: var(--warning); color: white; }
  .toggle-btn.active.OD { background: var(--info); color: white; }

  .status-chip { display: inline-flex; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
  .chip-present { background: var(--success-bg); color: var(--success); }
  .chip-absent { background: var(--danger-bg); color: var(--danger); }
  .chip-late { background: var(--warning-bg); color: var(--warning); }
  .chip-onleave { background: var(--info-bg); color: var(--info); }

  /* Login Panel */
  .login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg); }
  .login-card { width: 100%; max-width: 400px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px; padding: 40px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); }
  .input { width: 100%; height: 44px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg); padding: 0 16px; font-size: 14px; margin-bottom: 20px; outline: none; }
  .input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-light); }

  /* Overlay Components */
  .toast { position: fixed; top: 24px; right: 24px; padding: 16px 24px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; box-shadow: var(--sh-md); z-index: 1000; display: flex; align-items: center; gap: 12px; animation: slideIn 0.3s ease-out; }
  @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

  /* Mobile Adapters */
  @media (max-width: 768px) {
    .sidebar { transform: translateX(-100%); width: 100%; height: auto; bottom: 0; top: auto; flex-direction: row; border-right: none; border-top: 1px solid var(--border); padding-bottom: env(safe-area-inset-bottom); }
    .main-content { margin-left: 0; padding-bottom: 80px; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
    .header { padding: 0 20px; }
    .sidebar-header { display: none; }
    .nav-label { display: none; }
    .nav-group { display: flex; justify-content: space-around; width: 100%; }
    .nav-item { flex-direction: column; gap: 4px; font-size: 10px; border-left: none; border-top: 3px solid transparent; }
    .nav-item.active { border-top-color: var(--primary); background: transparent; }
  }
`;

/**
 * ━━━ UI ATOMS ━━━
 */

const Button = ({ children, variant = 'primary', className = '', ...props }) => {
  const btnClasses = `button btn-${variant} ${className}`;
  return <button className={btnClasses} {...props}>{children}</button>;
};

const Card = ({ children, className = '', ...props }) => (
  <div className={`card ${className}`} {...props}>{children}</div>
);

const Badge = ({ children, status }) => {
  const statusClasses = {
    Present: 'chip-present',
    Absent: 'chip-absent',
    Late: 'chip-late',
    'On Duty': 'chip-onleave',
    P: 'chip-present',
    A: 'chip-absent',
    L: 'chip-late',
    OD: 'chip-onleave'
  };
  return <span className={`status-chip ${statusClasses[status] || ''}`}>{children}</span>;
};

/**
 * ━━━ DYNAMIC VIEWS ━━━
 */

const DashboardView = ({ stats, shortfall }) => (
  <div className="view-container">
    <div className="stats-grid">
      <Card>
        <div className="stat-label">Total Students</div>
        <div className="stat-value">{stats.total}</div>
        <div className="stat-trend trend-up"><ChevronRight size={14} /> CS Department</div>
      </Card>
      <Card>
        <div className="stat-label">Present Today</div>
        <div className="stat-value">{stats.present}</div>
        <div className="stat-trend trend-up"><CheckCircle2 size={14} /> 92% Dynamic Avg</div>
      </Card>
      <Card>
        <div className="stat-label">Absent Today</div>
        <div className="stat-value">{stats.absent}</div>
        <div className="stat-trend trend-down"><AlertCircle size={14} /> Action Required</div>
      </Card>
      <Card>
        <div className="stat-label">Leave Pending</div>
        <div className="stat-value">{stats.leaves}</div>
        <div className="stat-trend info-color"><Clock size={14} /> 2 Overlapping</div>
      </Card>
    </div>

    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 0.8fr)', gap: '32px' }}>
      <Card style={{ minHeight: '400px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 600 }}>Attendance Metrics (6 Days)</h3>
          <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--primary)' }}></span> Participation
            </span>
          </div>
        </div>
        <div style={{ height: '300px', width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={stats.chartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
              <RechartsTooltip cursor={{ fill: 'var(--bg)' }} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
              <Bar dataKey="val" fill="var(--primary)" radius={[4, 4, 0, 0]} barSize={34} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card>
        <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '20px' }}>Defaulter Insights (Critical)</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {shortfall.slice(0, 5).map(s => (
            <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '14px', paddingBottom: '16px', borderBottom: '1px solid var(--border)' }}>
              <div className="avatar" style={{ background: '#FEE2E2', color: '#EF4444' }}>{s.name.substring(0, 2).toUpperCase()}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '14px', fontWeight: 600 }}>{s.name}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{s.roll}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--danger)' }}>{s.attendance}%</div>
                <div style={{ fontSize: '10px', fontWeight: 800, color: 'var(--danger)', opacity: 0.6 }}>RISK</div>
              </div>
            </div>
          ))}
        </div>
        <Button variant="ghost" style={{ width: '100%', marginTop: '20px' }}>Full Analytics Report</Button>
      </Card>
    </div>
  </div>
);

const AttendanceView = ({ onSave }) => {
  const [selectedSub, setSelectedSub] = useState('');
  const [roster, setRoster] = useState([]);
  const [query, setQuery] = useState('');
  
  const handleSelection = (id) => {
    setSelectedSub(id);
    const sub = SUBJECTS.find(s => s.id === id);
    if (sub) {
      const baseList = sub.id.includes('CS303') ? STUDENTS_B : STUDENTS_A;
      setRoster(baseList.map(s => ({ ...s, status: 'Present' })));
    }
  };

  const updateStatus = (id, status) => {
    setRoster(prev => prev.map(s => s.id === id ? { ...s, status } : s));
  };

  const setBulkStatus = (st) => {
    setRoster(prev => prev.map(s => ({ ...s, status: st })));
  };

  const filtered = roster.filter(s => 
    s.name.toLowerCase().includes(query.toLowerCase()) || 
    s.roll.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="view-container">
      <div className="selection-bar">
        <div className="input-group">
          <label className="input-label">Curriculum Subject</label>
          <select className="select" value={selectedSub} onChange={e => handleSelection(e.target.value)}>
            <option value="">Choose academic target...</option>
            {SUBJECTS.map(s => <option key={s.id} value={s.id}>{s.name} — {s.batch}</option>)}
          </select>
        </div>
        <div className="input-group" style={{ maxWidth: '200px' }}>
          <label className="input-label">Academic Date</label>
          <input type="date" className="select" defaultValue={new Date().toISOString().split('T')[0]} />
        </div>
        <div className="input-group" style={{ maxWidth: '200px' }}>
          <label className="input-label">Lecture Period</label>
          <select className="select">
            <option>Slot 1 (9-10 AM)</option>
            <option>Slot 2 (10-11 AM)</option>
            <option>Slot 3 (11-12 PM)</option>
          </select>
        </div>
      </div>

      <Card style={{ padding: '0' }}>
        <div style={{ padding: '20px 30px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ position: 'relative', width: '320px' }}>
            <Search size={16} style={{ position: 'absolute', left: '14px', top: '12px', color: 'var(--text-muted)' }} />
            <input 
              type="text" 
              className="select" 
              placeholder="Search Student..." 
              style={{ paddingLeft: '40px' }}
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', gap: '14px' }}>
            <Button variant="ghost" onClick={() => setBulkStatus('Present')}>All Present</Button>
            <Button variant="ghost" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }} onClick={() => setBulkStatus('Absent')}>All Absent</Button>
          </div>
        </div>

        <div style={{ overflowX: 'auto', maxHeight: '550px' }}>
          <table className="roster-table">
            <thead className="roster-header">
              <tr>
                <th style={{ width: '300px' }}>Identity</th>
                <th>Roll No</th>
                <th>Academic Status</th>
                <th style={{ textAlign: 'center' }}>Marking Console</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(st => (
                <tr key={st.id} className="roster-row">
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <div className="avatar" style={{ width: 34, height: 34 }}>{st.name.substring(0,2).toUpperCase()}</div>
                      <div style={{ fontWeight: 600 }}>{st.name}</div>
                    </div>
                  </td>
                  <td className="font-mono" style={{ fontSize: '13px', opacity: 0.7 }}>{st.roll}</td>
                  <td><Badge status={st.status}>{st.status}</Badge></td>
                  <td>
                    <div style={{ display: 'flex', justifyContent: 'center' }}>
                      <div className="status-toggle">
                        {['P', 'A', 'L', 'OD'].map(choice => (
                          <button 
                            key={choice}
                            className={`toggle-btn ${st.status.startsWith(choice) ? 'active ' + choice : ''}`}
                            onClick={() => updateStatus(st.id, { P: 'Present', A: 'Absent', L: 'Late', OD: 'On Duty' }[choice])}
                          >
                            {choice}
                          </button>
                        ))}
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div style={{ padding: '100px 40px', textAlign: 'center' }}>
              <Users size={56} strokeWidth={1.5} style={{ color: 'var(--text-muted)', marginBottom: '16px', opacity: 0.5 }} />
              <p style={{ color: 'var(--text-secondary)', fontSize: '15px' }}>Waiting for subject context selection...</p>
            </div>
          )}
        </div>
      </Card>

      {selectedSub && (
        <div style={{ 
          position: 'fixed', bottom: '40px', left: 'calc(50% + 120px)', transform: 'translateX(-50%)',
          width: '640px', background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: '20px',
          padding: '18px 36px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)', display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', zIndex: 1001, borderTop: '4px solid var(--primary)'
        }}>
          <div style={{ display: 'flex', gap: '30px' }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>Present</div>
              <div style={{ fontSize: '20px', fontWeight: 800 }}>{roster.filter(s => s.status === 'Present').length}</div>
            </div>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>Absent</div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--danger)' }}>{roster.filter(s => s.status === 'Absent').length}</div>
            </div>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>Marked</div>
              <div style={{ fontSize: '20px', fontWeight: 800 }}>{roster.length}</div>
            </div>
          </div>
          <Button onClick={() => onSave(roster)} style={{ height: '50px', padding: '0 32px', borderRadius: '12px' }}>Finalize & Sync Session</Button>
        </div>
      )}
    </div>
  );
};

/**
 * ━━━ APPLICATION CORE ━━━
 */

export default function FacultyAttendanceModule() {
  const [state, setState] = useState(INITIAL_STATE);
  const [view, setView] = useState('dashboard');
  const [toast, setToast] = useState(null);
  const [authForm, setAuthForm] = useState({ email: '', password: '' });

  useEffect(() => {
    document.body.className = state.darkMode ? 'dark' : '';
  }, [state.darkMode]);

  const handleLogin = (e) => {
    e.preventDefault();
    if (authForm.email === 'priya@dypatil.edu' && authForm.password === 'admin123') {
      const user = MOCK_FACULTY;
      setState(s => ({ ...s, user, isAuthenticated: true }));
      localStorage.setItem('faculty_user', JSON.stringify(user));
    } else {
      alert('Authentication Failed. Use: priya@dypatil.edu / admin123');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('faculty_user');
    setState(s => ({ ...s, user: null, isAuthenticated: false }));
  };

  const triggerToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const onAttendanceSubmit = (data) => {
    triggerToast(`Session Synced: ${data.length} student records committed.`);
    setView('dashboard');
  };

  const dashboardStats = useMemo(() => {
    const students = [...STUDENTS_A, ...STUDENTS_B];
    const riskList = students.filter(s => s.attendance < 75).sort((a,b) => a.attendance - b.attendance);
    return {
      total: students.length,
      present: Math.round(students.length * 0.92),
      absent: Math.round(students.length * 0.08),
      leaves: 3,
      chartData: [{ day: 'M', val: 92 }, { day: 'T', val: 89 }, { day: 'W', val: 95 }, { day: 'T', val: 91 }, { day: 'F', val: 90 }, { day: 'S', val: 84 }],
      shortfall: riskList
    };
  }, []);

  if (!state.isAuthenticated) {
    return (
      <div className="login-page">
        <style>{CSS_VARIABLES}</style>
        <div className="login-card">
          <div style={{ textAlign: 'center', marginBottom: '36px' }}>
            <div className="logo-box" style={{ margin: '0 auto 16px', borderRadius: '12px', width: '48px', height: '48px' }}><LayoutDashboard size={24} /></div>
            <h2 style={{ fontSize: '26px', fontWeight: 800, letterSpacing: '-0.03em' }}>Institutional Access</h2>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '8px' }}>Faculty Portal — CS Department</p>
          </div>
          <form onSubmit={handleLogin}>
            <label className="input-label">Academic Email</label>
            <input type="email" className="input" placeholder="p.sharma@institution.edu" value={authForm.email} onChange={e => setAuthForm({...authForm, email: e.target.value})} required />
            <label className="input-label">Personal Access Key</label>
            <input type="password" className="input" placeholder="••••••••" value={authForm.password} onChange={e => setAuthForm({...authForm, password: e.target.value})} required />
            <Button type="submit" style={{ width: '100%', height: '52px', fontSize: '15px' }}>Authorize Session</Button>
          </form>
          <div style={{ marginTop: '30px', padding: '16px', background: 'var(--bg)', borderRadius: '12px', border: '1px dashed var(--border)', fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center' }}>
            <strong>Demo Keyframe:</strong> priya@dypatil.edu / admin123
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <style>{CSS_VARIABLES}</style>
      
      {toast && <div className="toast"><CheckCircle2 size={20} color="var(--success)" /> <span>{toast}</span></div>}

      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-box" style={{ background: 'var(--primary)' }}><Smartphone size={18} /></div>
          <span className="logo-text">AcademicCore</span>
        </div>
        
        <div className="nav-group">
          <div className="nav-label">Central Control</div>
          <div className={`nav-item ${view === 'dashboard' ? 'active' : ''}`} onClick={() => setView('dashboard')}><LayoutDashboard size={18} /> Dashboard</div>
          <div className={`nav-item ${view === 'attendance' ? 'active' : ''}`} onClick={() => setView('attendance')}><UserCheck size={18} /> Marking Console</div>
          <div className={`nav-item ${view === 'students' ? 'active' : ''}`} onClick={() => setView('students')}><Users size={18} /> Student Roster</div>
          
          <div className="nav-label">Operational Analysis</div>
          <div className={`nav-item ${view === 'analytics' ? 'active' : ''}`} onClick={() => setView('analytics')}><BarChart3 size={18} /> Reports</div>
          <div className={`nav-item ${view === 'leaves' ? 'active' : ''}`} onClick={() => setView('leaves')}><FileText size={18} /> Requests</div>
          
          <div className="nav-label">Workspace Sub-System</div>
          <div className={`nav-item ${view === 'settings' ? 'active' : ''}`} onClick={() => setView('settings')}><Settings size={18} /> Preferences</div>
          <div className="nav-item" style={{ marginTop: 'auto', marginBottom: '24px', color: 'var(--danger)' }} onClick={handleLogout}><LogOut size={18} /> Termination</div>
        </div>
      </aside>

      <main className="main-content">
        <header className="header">
          <div className="page-title">{view.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
          <div className="header-actions">
            <button className="icon-btn" onClick={() => setState({...state, darkMode: !state.darkMode})}>{state.darkMode ? <Sun size={18} /> : <Moon size={18} />}</button>
            <button className="icon-btn"><Bell size={18} /><div className="badge-dot"></div></button>
            <div className="user-profile">
              <div className="user-info" style={{ textAlign: 'right' }}>
                <div className="user-name">{state.user.name}</div>
                <div className="user-role">{state.user.dept} • CS Senior Role</div>
              </div>
              <div className="avatar" style={{ borderRadius: '12px' }}>{state.user.avatar}</div>
            </div>
          </div>
        </header>

        <section className="content-area">
          <div style={{ marginBottom: '36px' }}>
            <h2 style={{ fontSize: '26px', fontWeight: 800, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>
              {view === 'dashboard' ? `Welcome back, Controller Sharma 👋` : view.charAt(0).toUpperCase() + view.slice(1)}
            </h2>
            <p style={{ color: 'var(--text-secondary)', marginTop: '6px', fontSize: '15px' }}>
              {view === 'dashboard' ? `Institutional Overview — ${new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}` : `Active session management for internal academic workflows.`}
            </p>
          </div>

          {view === 'dashboard' && <DashboardView stats={dashboardStats} shortfall={dashboardStats.shortfall} />}
          {view === 'attendance' && <AttendanceView onSave={onAttendanceSubmit} />}
          
          {['students', 'analytics', 'leaves', 'settings'].includes(view) && (
            <div style={{ minHeight: '450px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: '24px', textAlign: 'center', padding: '40px' }}>
              <div style={{ width: '92px', height: '92px', borderRadius: '50%', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '24px', color: 'var(--primary)' }}>
                {view === 'students' ? <Users size={36} /> : view === 'analytics' ? <BarChart3 size={36} /> : view === 'leaves' ? <FileText size={36} /> : <Settings size={36} />}
              </div>
              <h3 style={{ fontSize: '20px', fontWeight: 700 }}>{view.charAt(0).toUpperCase() + view.slice(1)} Sub-Module</h3>
              <p style={{ color: 'var(--text-secondary)', marginTop: '12px', maxWidth: '340px', lineHeight: 1.6 }}>This environment is being synchronized with the master database. Please refer to the Dashboard or Marking Console for active operations.</p>
              <Button style={{ marginTop: '30px', padding: '0 28px' }} onClick={() => setView('dashboard')}>Return to Command Hub</Button>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
