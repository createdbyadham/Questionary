import axios from 'axios';
import { Question, QuestionSet, QuizResult, ReviewResult } from '../types';

const api = axios.create({
  baseURL: 'http://localhost:5001',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true  // Enable sending cookies with requests
});

// Add request interceptor for logging
api.interceptors.request.use(
  (config) => {
    // Add Authorization header if token exists
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    console.log('API Request:', {
      method: config.method,
      url: config.url,
      data: config.data,
      params: config.params,
    });
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for logging
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', {
      status: response.status,
      data: response.data,
    });
    return response;
  },
  (error) => {
    console.error('API Response Error:', error);
    return Promise.reject(error);
  }
);

export const getQuestionSets = async (): Promise<QuestionSet[]> => {
  const response = await api.get('/api/question-sets');
  return response.data;
};

export const uploadQuestions = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('set_name', file.name.split('.')[0]); // Use filename as set name
  
  const response = await api.post('/api/upload-file', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getUploadProgress = async (sessionId: string): Promise<{ status: string; message: string; percent: number }> => {
  try {
    const response = await api.get(`/api/upload-progress/${sessionId}`);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return {
        status: 'error',
        message: 'Upload session not found or expired',
        percent: 0
      };
    }
    throw error;
  }
};

export const deleteSet = async (setId: number): Promise<{ message: string }> => {
  const response = await api.delete(`/api/question-sets/${setId}`);
  return response.data;
};

export const updateSetName = async (
  setId: number,
  newName: string
): Promise<{ message: string }> => {
  const response = await api.put(`/api/question-sets/${setId}/name`, { 
    name: newName 
  });
  return response.data;
};

export const startQuiz = async (
  selectedSets: number[],
  questionsPerQuiz: number = 40
): Promise<Question[]> => {
  const response = await api.post('/api/get_quiz', { 
    selected_sets: selectedSets,
    questions_per_quiz: questionsPerQuiz 
  });
  return response.data;
};

export const startReview = async (): Promise<Question[]> => {
  console.log('Starting review...');
  const response = await api.get('/review_incorrect');
  console.log('Review response:', response.data);
  return response.data;
};

export const submitQuiz = async (
  setId: number,
  answers: Record<string, string>
): Promise<QuizResult> => {
  console.log('Submitting answers:', answers);
  
  // Transform answers from Record to array of objects
  const formattedAnswers = Object.entries(answers).map(([questionId, answer]) => ({
    question_id: parseInt(questionId),
    selected_answer: answer
  }));
  
  const response = await api.post('/api/submit_quiz', {
    set_id: setId,
    answers: formattedAnswers
  });
  return response.data;
};

export const submitReview = async (
  answers: Record<string, string>
): Promise<ReviewResult> => {
  console.log('Submitting review answers:', answers);
  const response = await api.post('/api/submit_review', { answers });
  return response.data;
};
