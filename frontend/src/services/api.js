import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://recommendations.vosmos.events:7006/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (data) => api.post('/auth/register', data).then(res => res.data),
  login: (credentials) => api.post('/auth/login', credentials).then(res => res.data),
  getMe: () => api.get('/auth/me').then(res => res.data),
  uploadReferencePhotos: (files) => {
    const formData = new FormData();
    files.forEach(file => formData.append('photos', file));
    return api.post('/auth/upload-reference-photos', formData).then(res => res.data);
  },
  getMyReferencePhotos: () => api.get('/auth/my-reference-photos').then(res => res.data),
  deleteReferencePhoto: (photoId) => api.delete(`/auth/reference-photos/${photoId}`).then(res => res.data),
  triggerGalleryScan: () => api.post('/auth/trigger-gallery-scan').then(res => res.data),
};

export const galleryAPI = {
  createEmpty: () => api.post('/galleries/create').then(res => res.data),
  createAndUpload: (files) => {
    const formData = new FormData();
    files.forEach(file => formData.append('photos', file));
    return api.post('/galleries/upload', formData).then(res => res.data);
  },
  addPhotosToGallery: (galleryId, files) => {
    const formData = new FormData();
    files.forEach(file => formData.append('photos', file));
    return api.post(`/galleries/${galleryId}/add-photos`, formData).then(res => res.data);
  },
  getMyGalleries: () => api.get('/galleries/my-galleries').then(res => res.data),
  getByToken: (shareToken) => api.get(`/galleries/${shareToken}`).then(res => res.data),
  getAllPhotos: (shareToken, page = 1, pageSize = 50) =>
    api.get(`/galleries/${shareToken}/all-photos`, {
      params: { page, page_size: pageSize }
    }).then(res => res.data),
  getMyPhotos: (shareToken, page = 1, pageSize = 50) =>
    api.get(`/galleries/${shareToken}/my-photos-with-confidence`, {
      params: { page, page_size: pageSize }
    }).then(res => res.data),
  getStatus: (shareToken) => api.get(`/galleries/${shareToken}/status`).then(res => res.data),
  deletePhoto: (shareToken, photoId) => api.delete(`/galleries/${shareToken}/photos/${photoId}`).then(res => res.data),
  tagKnownPeople: (shareToken) => api.post(`/galleries/${shareToken}/tag-known-people`).then(res => res.data),
};

export default api;