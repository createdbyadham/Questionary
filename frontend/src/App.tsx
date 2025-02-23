import React, { useState } from 'react';
import { ChakraProvider, Box, extendTheme } from '@chakra-ui/react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AppRoutes from './routes';
import { Question } from './types';
import { Home } from './pages/Home';
import { Quiz } from './pages/Quiz';
import { startReview } from './api';
import { AuthProvider } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import ProtectedRoute from './components/ProtectedRoute';

const theme = extendTheme({
  styles: {
    global: {
      body: {
        bg: '#111111',
        color: 'white',
      },
    },
  },
  colors: {
    gray: {
      900: '#111111', // Main background
      850: '#161616', // Subtle highlight
      800: '#1c1c1c', // Card background
      750: '#202020', // Subtle highlight
      700: '#2a2a2a', // Lighter elements
      600: '#363636',
      500: '#494949',
      400: '#636363',
      300: '#7c7c7c',
      200: '#a0a0a0',
      100: '#cfcfcf',
      50: '#f7f7f7',
    },
    blue: {
      500: '#173150', // Base blue
      600: '#132740', // Darker blue
      700: '#0f1f33', // Even darker
      800: '#0b1726', // Darkest blue
      900: '#070f19',
    },
  },
  components: {
    Button: {
      baseStyle: {
        _hover: {
          transform: 'translateY(-2px)',
          boxShadow: 'lg',
        },
        _active: {
          transform: 'translateY(0)',
        },
      },
    },
    Progress: {
      baseStyle: {
        track: {
          bg: 'gray.700',
        },
        filledTrack: {
          bg: 'blue.500',
        },
      },
    },
  },
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  const [currentQuestions, setCurrentQuestions] = useState<Question[] | null>(null);
  const [isReview, setIsReview] = useState(false);

  const handleStartQuiz = (questions: Question[]) => {
    setCurrentQuestions(questions);
    setIsReview(false);
  };

  const handleReviewIncorrect = async () => {
    try {
      const reviewQuestions = await startReview();
      setCurrentQuestions(reviewQuestions);
      setIsReview(true);
    } catch (error) {
      console.error('Error starting review:', error);
    }
  };

  const handleRetakeQuiz = () => {
    setCurrentQuestions(null);
    setIsReview(false);
  };

  const handleBackToSets = () => {
    setCurrentQuestions(null);
    setIsReview(false);
  };

  return (
    <AuthProvider>
      <ChakraProvider theme={theme}>
        <QueryClientProvider client={queryClient}>
          <Router>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <Box
                      minH="100vh"
                      bg="gray.900"
                      position="relative"
                    >
                      {currentQuestions ? (
                        <Quiz
                          questions={currentQuestions}
                          onReviewIncorrect={handleReviewIncorrect}
                          onRetakeQuiz={handleRetakeQuiz}
                          onBackToSets={handleBackToSets}
                          isReview={isReview}
                        />
                      ) : (
                        <Home onStartQuiz={handleStartQuiz} />
                      )}
                    </Box>
                  </ProtectedRoute>
                }
              />
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </Router>
        </QueryClientProvider>
      </ChakraProvider>
    </AuthProvider>
  );
}

export default App;
