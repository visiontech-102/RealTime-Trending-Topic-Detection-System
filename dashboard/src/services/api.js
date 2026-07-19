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

export const loginUser = async (email, password) => {
  // FastAPI OAuth2PasswordRequestForm expects form-data
  const formData = new URLSearchParams();
  formData.append('username', email); // Use email as the username
  formData.append('password', password);

  const response = await api.post('/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  });
  return response.data;
};

export const signupUser = async (username, email, password) => {
  const response = await api.post('/auth/signup', { username, email, password });
  return response.data;
};

export const loginWithGoogle = async (credential) => {
  const response = await api.post('/auth/google', { credential });
  return response.data;
};

export const changeUserPassword = async (currentPassword, newPassword) => {
  const response = await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword
  });
  return response.data;
};

export const get2FAStatus = async () => {
  const response = await api.get('/auth/2fa/status');
  return response.data;
};

export const request2FACode = async () => {
  const response = await api.post('/auth/2fa/send-code');
  return response.data;
};

export const verify2FACode = async (code) => {
  const response = await api.post('/auth/2fa/verify', { code });
  return response.data;
};

export const disable2FA = async () => {
  const response = await api.post('/auth/2fa/disable');
  return response.data;
};

export const getPreferences = async () => {
  const response = await api.get('/auth/preferences');
  return response.data;
};

export const updatePreferences = async (preferences) => {
  const response = await api.post('/auth/preferences', preferences);
  return response.data;
};

const buildDateQuery = (dateParams = {}) => {
  const params = new URLSearchParams();
  if (dateParams.from_date) params.append('from_date', dateParams.from_date);
  if (dateParams.to_date) params.append('to_date', dateParams.to_date);
  const qs = params.toString();
  return qs ? `&${qs}` : '';
};

export const getTrends = async (lang = 'en', dateParams = {}) => {
  const response = await api.get(`/trends?lang=${lang}&limit=50${buildDateQuery(dateParams)}`);
  return response.data;
};

export const getHistory = async (lang = 'en', dateParams = {}, limit = 50) => {
  const response = await api.get(`/history?lang=${lang}&limit=${limit}${buildDateQuery(dateParams)}`);
  return response.data;
};

export const filterTrends = async (keyword, lang = 'en') => {
  const response = await api.post(`/filter?keyword=${keyword}&lang=${lang}`);
  return response.data;
};

export const getRawTweets = async (lang = 'en', dateParams = {}, limit = 50) => {
  const response = await api.get(`/raw_tweets?lang=${lang}&limit=${limit}${buildDateQuery(dateParams)}`);
  return response.data;
};

export const getHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export const getModelComparison = async () => {
  const response = await api.get('/models/comparison');
  return response.data;
};

export const runModelComparison = async () => {
  const response = await api.post('/jobs/run-comparison');
  return response.data;
};

export const trainLda = async () => {
  const response = await api.post('/jobs/train-lda');
  return response.data;
};

export const trainBertopic = async () => {
  const response = await api.post('/jobs/train-bertopic');
  return response.data;
};

export const trainNmf = async () => {
  const response = await api.post('/jobs/train-nmf');
  return response.data;
};

export const getVisualizationUrl = (model) =>
  `http://localhost:8000/visualizations/${model}`;

export const getTopicTrends = async (dateParams = {}) => {
  const response = await api.get(`/trends/topics_over_time?${buildDateQuery(dateParams).replace(/^&/, '')}`);
  return response.data;
};

export const getTrendingKeywords = async (dateParams = {}) => {
  const response = await api.get(`/trends/keywords?${buildDateQuery(dateParams).replace(/^&/, '')}`);
  return response.data;
};

export const getTweetStats = async (dateParams = {}) => {
  const response = await api.get(`/tweets/stats?${buildDateQuery(dateParams).replace(/^&/, '')}`);
  return response.data;
};

export const getModelStatus = async () => {
  const response = await api.get('/models/status');
  return response.data;
};

export const getModelHistory = async (limit = 20, dateParams = {}) => {
  const response = await api.get(`/models/history?limit=${limit}${buildDateQuery(dateParams)}`);
  return response.data;
};

