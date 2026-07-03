import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const Layout = ({ children, title, role }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const adminMenu = [
    {
      section: 'Overview',
      links: [
        { name: 'Dashboard', path: '/admin', icon: 'fa-solid fa-gauge-high' },
        { name: 'Analytics', path: '/admin/analytics', icon: 'fa-solid fa-chart-line' },
      ]
    },
    {
      section: 'Management',
      links: [
        { name: 'Students', path: '/admin/students', icon: 'fa-solid fa-users' },
        { name: 'Faculty', path: '/admin/faculty', icon: 'fa-solid fa-chalkboard-user' },
        { name: 'Faculty Alot', path: '/admin/faculty_assignments', icon: 'fa-solid fa-link' },
        { name: 'Subjects', path: '/admin/subjects', icon: 'fa-solid fa-book' },
        { name: 'HR / Payroll', path: '/admin/hr', icon: 'fa-solid fa-user-tie' },
      ]
    },
    {
      section: 'Academic',
      links: [
        { name: 'Attendance Portal', path: '/admin/attendance', icon: 'fa-solid fa-calendar-check' },
        { name: 'Timetable Manager', path: '/admin/timetable', icon: 'fa-solid fa-table-cells' },
      ]
    },
    {
      section: 'Examinations & Marks',
      links: [
        { name: 'Results / Marks', path: '/admin/results', icon: 'fa-solid fa-square-poll-vertical' },
      ]
    },
    {
      section: 'Communication',
      links: [
        { name: 'Notifications', path: '/admin/notifications', icon: 'fa-solid fa-bell' },
      ]
    }
  ];

  const facultyMenu = [
    {
      section: 'Academic',
      links: [
        { name: 'Dashboard', path: '/faculty', icon: 'fa-solid fa-gauge-high' },
        { name: 'Attendance Portal', path: '/faculty/attendance', icon: 'fa-solid fa-calendar-check' },
        { name: 'Timetable', path: '/faculty/timetable', icon: 'fa-solid fa-table-cells' },
      ]
    },
    {
      section: 'Examinations',
      links: [
        { name: 'Upload Results', path: '/faculty/results', icon: 'fa-solid fa-square-poll-vertical' },
      ]
    },
    {
      section: 'Account',
      links: [
        { name: 'Leave Application', path: '/faculty/leave', icon: 'fa-solid fa-calendar-minus' },
      ]
    }
  ];

  const studentMenu = [
    {
      section: 'Main',
      links: [
        { name: 'Dashboard', path: '/student', icon: 'fa-solid fa-gauge-high' },
        { name: 'Attendance', path: '/student/attendance', icon: 'fa-solid fa-calendar-check' },
        { name: 'Timetable', path: '/student/timetable', icon: 'fa-solid fa-table-cells' },
        { name: 'My Marks', path: '/student/results', icon: 'fa-solid fa-graduation-cap' },
      ]
    },
    {
      section: 'Academic',
      links: [
        { name: 'Notifications', path: '/student/notifications', icon: 'fa-solid fa-bell' },
      ]
    }
  ];

  const menu = role === 'admin' ? adminMenu : role === 'faculty' ? facultyMenu : studentMenu;
  const avColor = role === 'faculty' ? '#7C3AED' : role === 'student' ? '#059669' : '#2563EB';
  const avLetter = user?.name ? user.name[0].toUpperCase() : 'A';

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  useEffect(() => {
    if (sidebarOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [sidebarOpen]);

  return (
    <div className={user?.dark_mode ? "dark-theme" : ""}>
      <button className="sb-toggle" id="sbToggle" onClick={toggleSidebar}>
        <i className="fa-solid fa-bars"></i>
      </button>
      <div 
        className={`sb-overlay ${sidebarOpen ? 'show' : ''}`} 
        id="sbOverlay" 
        onClick={closeSidebar}
      ></div>

      <div className="shell">
        <div className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
          <div className="sb-brand">
            <img src="/static/images/dypatil_logo.png" className="sb-logo-img" alt="DY Patil" />
            <div>
              <div className="sb-bname">DY Patil ERP</div>
              <div className="sb-bsub">{role.charAt(0).toUpperCase() + role.slice(1)} Portal</div>
            </div>
          </div>
          
          <div className="sb-nav">
            {menu.map((sec) => (
              <React.Fragment key={sec.section}>
                <div className="sb-sec">{sec.section}</div>
                {sec.links.map((link) => {
                  const isActive = location.pathname === link.path;
                  return (
                    <Link
                      key={link.name}
                      to={link.path}
                      className={`sb-link ${isActive ? 'active' : ''}`}
                      onClick={closeSidebar}
                    >
                      <i className={link.icon}></i> {link.name}
                    </Link>
                  );
                })}
              </React.Fragment>
            ))}
          </div>

          <div className="sb-foot">
            <div className="sb-user">
              <div className="sb-av" style={{ backgroundColor: avColor }}>
                {avLetter}
              </div>
              <div>
                <div className="sb-uname">{user?.name}</div>
                <div className="sb-urole">{role.charAt(0).toUpperCase() + role.slice(1)}</div>
              </div>
              <button onClick={handleLogout} className="sb-logout" title="Logout" style={{ border: 'none', background: 'none' }}>
                <i className="fa-solid fa-arrow-right-from-bracket"></i>
              </button>
            </div>
          </div>
        </div>

        <div className="topbar">
          <div className="tb-info">
            <div className="tb-ptitle">{title}</div>
            <div className="tb-crumb">
              <Link to={`/${role}`}>Home</Link> / {title}
            </div>
          </div>
        </div>

        <div className="main">
          {children}
        </div>
      </div>
    </div>
  );
};

