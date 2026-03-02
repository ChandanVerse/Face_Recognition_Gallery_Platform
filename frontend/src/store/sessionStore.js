import { create } from 'zustand';

const useSessionStore = create((set, get) => ({
  sessionId: null,
  galleryToken: null,

  // Initialize session from localStorage
  initialize: () => {
    const sessionId = localStorage.getItem('sessionId');
    const galleryToken = localStorage.getItem('galleryToken');
    if (sessionId) {
      set({ sessionId, galleryToken });
    }
  },

  // Set session ID
  setSessionId: (sessionId) => {
    localStorage.setItem('sessionId', sessionId);
    set({ sessionId });
  },

  // Set gallery token
  setGalleryToken: (galleryToken) => {
    localStorage.setItem('galleryToken', galleryToken);
    set({ galleryToken });
  },

  // Clear session
  clearSession: () => {
    localStorage.removeItem('sessionId');
    localStorage.removeItem('galleryToken');
    set({ sessionId: null, galleryToken: null });
  },
}));

export default useSessionStore;
