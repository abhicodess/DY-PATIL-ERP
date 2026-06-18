import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './routes/ProtectedRoute';

import './index.css';

// Import Pages
import { Login } from './pages/Login';
import { AdminDashboard } from './pages/admin/AdminDashboard';
import { ManageStudents } from './pages/admin/ManageStudents';
import { ManageFaculty } from './pages/admin/ManageFaculty';
import { ManageTimetable } from './pages/admin/ManageTimetable';
import { AdminAttendance } from './pages/admin/AdminAttendance';
import { ExamResults } from './pages/admin/ExamResults';
import { Notifications as AdminNotifications } from './pages/admin/Notifications';
import { HRModule } from './pages/admin/HRModule';

import { FacultyDashboard } from './pages/faculty/FacultyDashboard';
import { TakeAttendance } from './pages/faculty/TakeAttendance';
import { ViewTimetable } from './pages/faculty/ViewTimetable';
import { UploadResults } from './pages/faculty/UploadResults';
import { LeaveRequest } from './pages/faculty/LeaveRequest';

import { StudentDashboard } from './pages/student/StudentDashboard';
import { MyAttendance } from './pages/student/MyAttendance';
import { MyResults } from './pages/student/MyResults';
import { MyTimetable } from './pages/student/MyTimetable';
import { Notifications as StudentNotifications } from './pages/student/Notifications';
import { ReportGenerator } from './pages/shared/ReportGenerator';
import { ReportHistory } from './pages/shared/ReportHistory';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            
            {/* Admin Routes */}
            <Route path="/admin" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            } />
            <Route path="/admin/students" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <ManageStudents />
              </ProtectedRoute>
            } />
            <Route path="/admin/faculty" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <ManageFaculty />
              </ProtectedRoute>
            } />
            <Route path="/admin/timetable" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <ManageTimetable />
              </ProtectedRoute>
            } />
            <Route path="/admin/attendance" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminAttendance />
              </ProtectedRoute>
            } />
            <Route path="/admin/results" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <ExamResults />
              </ProtectedRoute>
            } />
            <Route path="/admin/notifications" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminNotifications />
              </ProtectedRoute>
            } />
            <Route path="/admin/hr" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <HRModule />
              </ProtectedRoute>
            } />
            <Route path="/admin/reports" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <ReportGenerator />
              </ProtectedRoute>
            } />
            <Route path="/admin/reports/history" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <ReportHistory />
              </ProtectedRoute>
            } />

            {/* Faculty Routes */}
            <Route path="/faculty" element={
              <ProtectedRoute allowedRoles={['faculty']}>
                <FacultyDashboard />
              </ProtectedRoute>
            } />
            <Route path="/faculty/attendance" element={
              <ProtectedRoute allowedRoles={['faculty']}>
                <TakeAttendance />
              </ProtectedRoute>
            } />
            <Route path="/faculty/timetable" element={
              <ProtectedRoute allowedRoles={['faculty']}>
                <ViewTimetable />
              </ProtectedRoute>
            } />
            <Route path="/faculty/results" element={
              <ProtectedRoute allowedRoles={['faculty']}>
                <UploadResults />
              </ProtectedRoute>
            } />
            <Route path="/faculty/leave" element={
              <ProtectedRoute allowedRoles={['faculty']}>
                <LeaveRequest />
              </ProtectedRoute>
            } />
            <Route path="/faculty/reports" element={
              <ProtectedRoute allowedRoles={['faculty']}>
                <ReportGenerator />
              </ProtectedRoute>
            } />
            <Route path="/faculty/reports/history" element={
              <ProtectedRoute allowedRoles={['faculty']}>
                <ReportHistory />
              </ProtectedRoute>
            } />

            {/* Student Routes */}
            <Route path="/student" element={
              <ProtectedRoute allowedRoles={['student']}>
                <StudentDashboard />
              </ProtectedRoute>
            } />
            <Route path="/student/attendance" element={
              <ProtectedRoute allowedRoles={['student']}>
                <MyAttendance />
              </ProtectedRoute>
            } />
            <Route path="/student/results" element={
              <ProtectedRoute allowedRoles={['student']}>
                <MyResults />
              </ProtectedRoute>
            } />
            <Route path="/student/timetable" element={
              <ProtectedRoute allowedRoles={['student']}>
                <MyTimetable />
              </ProtectedRoute>
            } />
            <Route path="/student/notifications" element={
              <ProtectedRoute allowedRoles={['student']}>
                <StudentNotifications />
              </ProtectedRoute>
            } />
            <Route path="/student/reports" element={
              <ProtectedRoute allowedRoles={['student']}>
                <ReportGenerator />
              </ProtectedRoute>
            } />
            <Route path="/student/reports/history" element={
              <ProtectedRoute allowedRoles={['student']}>
                <ReportHistory />
              </ProtectedRoute>
            } />

            {/* Default redirect for authenticated home requests */}
            <Route path="/" element={
              <ProtectedRoute>
                <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-purple-500" />
                </div>
              </ProtectedRoute>
            } />
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-purple-500" />
                </div>
              </ProtectedRoute>
            } />

            {/* Catch all fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
