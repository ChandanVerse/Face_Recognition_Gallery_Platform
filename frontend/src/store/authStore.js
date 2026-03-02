import { create } from 'zustand';
import { authAPI } from '../services/api';

const useAuthStore = create((set) => ({
  user: null,
  isAuthenticated: false,
  loading: false,
  error: null,

  // Initialize auth state from localStorage
  initialize: async () => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const user = await authAPI.getMe();
        set({ user, isAuthenticated: true });
      } catch (error) {
        localStorage.removeItem('token');
        set({ user: null, isAuthenticated: false });
      }
    }
  },

  register: async (userData) => {
    set({ loading: true, error: null });
    try {
      const response = await authAPI.register(userData);
      localStorage.setItem('token', response.access_token);
      const user = await authAPI.getMe();
      set({ user, isAuthenticated: true, loading: false });
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Registration failed';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  login: async (credentials) => {
    set({ loading: true, error: null });
    try {
      const response = await authAPI.login(credentials);
      localStorage.setItem('token', response.access_token);
      const user = await authAPI.getMe();
      set({ user, isAuthenticated: true, loading: false });
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Login failed';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, isAuthenticated: false });
  },

  clearError: () => {
    set({ error: null });
  },
}));

export default useAuthStore;