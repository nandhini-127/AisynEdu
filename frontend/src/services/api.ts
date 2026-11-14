import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const BASE_URL = (import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || '').trim();
export const API_BASE = BASE_URL ? `${BASE_URL.replace(/\/$/, '')}/api/v1` : '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000,
});

// Request Interceptor: Attach JWT Access Token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('edunex_access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Handle 401 Unauthorized & Token Expiration
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('edunex_refresh_token');
      // Attempt token refresh if refresh token exists and not already retrying
      if (refreshToken && !error.config?.url?.includes('/auth/refresh') && !error.config?.url?.includes('/auth/login')) {
        try {
          const res = await axios.post(`${API_BASE}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const newAccessToken = res.data?.data?.access_token;
          if (newAccessToken) {
            localStorage.setItem('edunex_access_token', newAccessToken);
            if (error.config) {
              error.config.headers.Authorization = `Bearer ${newAccessToken}`;
              return apiClient(error.config);
            }
          }
        } catch (refreshErr) {
          // Token refresh failed - clear tokens and force re-login
          localStorage.removeItem('edunex_access_token');
          localStorage.removeItem('edunex_refresh_token');
          localStorage.removeItem('edunex_user');
          if (window.location.pathname !== '/login') {
            window.location.href = '/login?expired=1';
          }
        }
      } else {
        localStorage.removeItem('edunex_access_token');
        localStorage.removeItem('edunex_refresh_token');
        localStorage.removeItem('edunex_user');
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;

