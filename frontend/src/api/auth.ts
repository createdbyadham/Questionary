import axios from 'axios';

const API_URL = 'http://localhost:5001/api';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true
});

// Add request interceptor for authentication
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export interface User {
  id: number;
  username: string;
  email: string;
}

export interface AuthResponse {
  message: string;
  access_token: string;
  user: User;
}

export const register = async (username: string, email: string, password: string): Promise<AuthResponse> => {
  const response = await api.post('/register', {
    username,
    email,
    password,
  });
  return response.data;
};

export const login = async (username: string, password: string): Promise<AuthResponse> => {
  const response = await api.post('/login', {
    username,
    password,
  });
  return response.data;
};

export const getCurrentUser = async (): Promise<{ user: User }> => {
  const response = await api.get('/user');
  return response.data;
};
