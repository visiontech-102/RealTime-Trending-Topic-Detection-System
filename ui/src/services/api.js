import axios from 'axios';

// Create Axios Instance
const api = axios.create({
  baseURL: 'http://localhost:8000',
});

// Since auth is optional in viewing trends for the demo, we won't strictly enforce interceptors here,
// but we leave room for token injection
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config;
});

export const getTrends = async (lang = 'en') => {
  const response = await api.get(`/trends?lang=${lang}`);
  return response.data;
};

export const getHistory = async (lang = 'en') => {
  const response = await api.get(`/history?lang=${lang}`);
  return response.data;
};

export const filterTrends = async (keyword, lang = 'en') => {
  const response = await api.post(`/filter?keyword=${keyword}&lang=${lang}`);
  return response.data;
};
