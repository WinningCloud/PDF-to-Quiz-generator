import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8080/api', // Matches your backend prefix
});

// Automatically add the Bearer token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;