import apiClient from './api';
import { AuthTokens, LoginPayload, RegisterPayload, User } from '../types/auth';
import { notesService } from './notesService';

export const authService = {
  async register(payload: RegisterPayload): Promise<{ user: User; tokens: AuthTokens }> {
    const res = await apiClient.post('/auth/register', payload);
    const data = res.data?.data;
    if (data?.access_token) {
      localStorage.setItem('edunex_access_token', data.access_token);
      localStorage.setItem('edunex_refresh_token', data.refresh_token);
      localStorage.setItem('edunex_user', JSON.stringify(data.user));
    }
    return data;
  },

  async login(payload: LoginPayload): Promise<{ user: User; tokens: AuthTokens }> {
    const res = await apiClient.post('/auth/login', payload);
    const data = res.data?.data;
    if (data?.access_token) {
      localStorage.setItem('edunex_access_token', data.access_token);
      localStorage.setItem('edunex_refresh_token', data.refresh_token);
      localStorage.setItem('edunex_user', JSON.stringify(data.user));
      if (typeof data.streak_increased === 'boolean') {
        localStorage.setItem('edunex_streak_increased', String(data.streak_increased));
      }
    }
    return data;
  },

  async getCurrentUser(): Promise<User> {
    const res = await apiClient.get('/auth/me');
    const user = res.data?.data;
    localStorage.setItem('edunex_user', JSON.stringify(user));
    return user;
  },

  async updateProfile(updates: Partial<User>): Promise<User> {
    const res = await apiClient.patch('/auth/me', updates);
    const user = res.data?.data;
    localStorage.setItem('edunex_user', JSON.stringify(user));
    return user;
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } catch (e) {
      // Ignore network errors on logout
    } finally {
      notesService.clearUserCache();
      localStorage.removeItem('edunex_access_token');
      localStorage.removeItem('edunex_refresh_token');
      localStorage.removeItem('edunex_user');
      localStorage.removeItem('edunex_streak_increased');
      localStorage.removeItem('edunex_saved_study_notes');
    }
  },

  getStoredUser(): User | null {
    const raw = localStorage.getItem('edunex_user');
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('edunex_access_token');
  },
};

