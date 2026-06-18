import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading, isAuthenticated } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Handle root/dashboard redirection based on role
  if (location.pathname === '/' || location.pathname === '/dashboard') {
    if (user?.role === 'admin') return <Navigate to="/admin" replace />;
    if (user?.role === 'faculty') return <Navigate to="/faculty" replace />;
    if (user?.role === 'student') return <Navigate to="/student" replace />;
  }

  // Validate allowed roles for this route
  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <div className="glass max-w-md w-full p-8 rounded-2xl text-center">
          <h1 className="text-6xl font-bold text-red-500 mb-4">403</h1>
          <h2 className="text-2xl font-semibold text-slate-100 mb-2">Access Forbidden</h2>
          <p className="text-slate-400 mb-6">
            You do not have the required permissions to access this page.
          </p>
          <button
            onClick={() => window.history.back()}
            className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return children;
};
