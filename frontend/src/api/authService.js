import axios from 'axios';
import { useAuthStore } from '../store/useAuthStore';

export const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper to fetch CSRF token dynamically
const fetchCsrfToken = async () => {
  try {
    const response = await axios.get('/api/v1/auth/csrf', { withCredentials: true });
    const token = response.data.csrf_token || (response.data.data && response.data.data.csrf_token);
    useAuthStore.getState().setCsrfToken(token);
    return token;
  } catch (error) {
    console.error('Failed to fetch CSRF token', error);
    return null;
  }
};

// Request Interceptor
api.interceptors.request.use(
  async (config) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }

    // Mutating requests require CSRF token
    const method = config.method ? config.method.toUpperCase() : '';
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
      let csrfToken = useAuthStore.getState().csrfToken;
      if (!csrfToken) {
        csrfToken = await fetchCsrfToken();
      }
      if (csrfToken) {
        config.headers['X-CSRF-Token'] = csrfToken;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor for handling token refresh
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 Unauthorized errors
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Don't retry refresh, login, or logout requests
      if (originalRequest.url === '/auth/refresh' || originalRequest.url === '/auth/login' || originalRequest.url === '/auth/logout') {
        useAuthStore.getState().clearAuth();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers['Authorization'] = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshResponse = await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true });
        const newAccessToken = refreshResponse.data.access_token || (refreshResponse.data.data && refreshResponse.data.data.access_token);
        
        useAuthStore.getState().setAccessToken(newAccessToken);
        api.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;
        originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;
        
        processQueue(null, newAccessToken);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        useAuthStore.getState().clearAuth();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// Auth Service Endpoints
export const authService = {
  login: async (username, password, role) => {
    const response = await api.post('/auth/login', { username, password, role });
    const { access_token, user } = response.data.data;
    useAuthStore.getState().setAccessToken(access_token);
    useAuthStore.getState().setUser(user);
    await fetchCsrfToken();
    return response.data.data;
  },

  logout: async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      useAuthStore.getState().clearAuth();
    }
  },

  refreshToken: async () => {
    const response = await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true });
    const access_token = response.data.access_token || (response.data.data && response.data.data.access_token);
    useAuthStore.getState().setAccessToken(access_token);
    return access_token;
  },
};
