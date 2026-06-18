import React, { createContext, useContext, useEffect, useState } from 'react';
import { authService, api } from '../api/authService';
import { useAuthStore } from '../store/useAuthStore';
import { tenantService } from '../api/tenantService';

const AuthContext = createContext(null);
export const TenantContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const { user, accessToken, setUser, clearAuth } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [tenant, setTenant] = useState(null);
  const [tenantLoading, setTenantLoading] = useState(true);

  // Fetch tenant info on application load before auth check completes
  useEffect(() => {
    const fetchTenant = async () => {
      try {
        const response = await tenantService.getTenantInfo();
        const data = response.data; // Response is wrapped in standard API response { status: "success", data: { ... } }
        setTenant(data);
        if (data && data.primary_color) {
          document.documentElement.style.setProperty('--brand-color', data.primary_color);
        }
      } catch (error) {
        console.error('Failed to load tenant info:', error);
      } finally {
        setTenantLoading(false);
      }
    };
    fetchTenant();
  }, []);

  // Silent refresh on mount to restore session
  useEffect(() => {
    const initAuth = async () => {
      try {
        await authService.refreshToken();
        const response = await api.get('/auth/me');
        setUser(response.data.data);
      } catch (error) {
        clearAuth();
      } finally {
        setLoading(false);
      }
    };
    initAuth();
  }, [setUser, clearAuth]);

  const login = async (username, password, role) => {
    const data = await authService.login(username, password, role);
    return data.user;
  };

  const logout = async () => {
    await authService.logout();
  };

  const isAuthenticated = () => {
    return !!accessToken;
  };

  return (
    <TenantContext.Provider value={{ tenant, loading: tenantLoading }}>
      <AuthContext.Provider value={{ user, loading: loading || tenantLoading, login, logout, isAuthenticated }}>
        {children}
      </AuthContext.Provider>
    </TenantContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const useTenant = () => {
  const context = useContext(TenantContext);
  if (context === undefined) {
    throw new Error('useTenant must be used within a TenantProvider');
  }
  return context;
};
