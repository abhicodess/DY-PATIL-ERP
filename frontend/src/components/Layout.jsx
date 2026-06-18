import React from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut, LayoutDashboard, UserCheck, Users, Calendar, Award, Bell, ClipboardList, BookOpen } from 'lucide-react';

export const Layout = ({ children, title, role }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const adminMenu = [
    { name: 'Dashboard', path: '/admin', icon: LayoutDashboard },
    { name: 'Students', path: '/admin/students', icon: Users },
    { name: 'Faculty', path: '/admin/faculty', icon: UserCheck },
    { name: 'Timetable', path: '/admin/timetable', icon: Calendar },
    { name: 'Attendance', path: '/admin/attendance', icon: ClipboardList },
    { name: 'Results', path: '/admin/results', icon: Award },
    { name: 'Notifications', path: '/admin/notifications', icon: Bell },
    { name: 'HR Module', path: '/admin/hr', icon: BookOpen },
  ];

  const facultyMenu = [
    { name: 'Dashboard', path: '/faculty', icon: LayoutDashboard },
    { name: 'Take Attendance', path: '/faculty/attendance', icon: ClipboardList },
    { name: 'View Timetable', path: '/faculty/timetable', icon: Calendar },
    { name: 'Upload Results', path: '/faculty/results', icon: Award },
    { name: 'Leave Request', path: '/faculty/leave', icon: BookOpen },
  ];

  const studentMenu = [
    { name: 'Dashboard', path: '/student', icon: LayoutDashboard },
    { name: 'My Attendance', path: '/student/attendance', icon: ClipboardList },
    { name: 'My Results', path: '/student/results', icon: Award },
    { name: 'My Timetable', path: '/student/timetable', icon: Calendar },
    { name: 'Notifications', path: '/student/notifications', icon: Bell },
  ];

  const menu = role === 'admin' ? adminMenu : role === 'faculty' ? facultyMenu : studentMenu;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-white/5 flex flex-col justify-between p-4 hidden md:flex">
        <div className="flex flex-col gap-6">
          <div className="px-4 py-2 border-b border-white/5">
            <h2 className="text-xl font-bold text-white tracking-wide">DYP ERP</h2>
            <p className="text-xs text-purple-400 font-semibold uppercase tracking-wider mt-0.5">{role} Portal</p>
          </div>

          <nav className="flex flex-col gap-1">
            {menu.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-2.5 rounded-xl transition text-sm font-medium ${
                    isActive
                      ? 'bg-purple-600/20 text-purple-400 border border-purple-500/20'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-white/5'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex flex-col gap-4">
          <div className="px-4 py-2 border-t border-white/5 pt-4">
            <p className="text-sm font-semibold text-slate-200">{user?.name}</p>
            <p className="text-xs text-slate-400 mt-0.5">{user?.department || 'Main Campus'}</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-red-400 hover:bg-red-500/10 transition text-sm font-semibold text-left"
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Top Header */}
        <header className="bg-slate-900/60 backdrop-blur border-b border-white/5 px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-white">{title}</h1>
          <div className="flex items-center gap-4">
            <span className="text-xs bg-purple-500/20 text-purple-400 border border-purple-500/30 px-3 py-1 rounded-full font-bold capitalize">
              {role}
            </span>
          </div>
        </header>

        {/* View Main */}
        <main className="flex-1 p-6 overflow-y-auto bg-slate-950">
          {children}
        </main>
      </div>
    </div>
  );
};
