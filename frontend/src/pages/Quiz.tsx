import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  VStack,
  useToast,
  Text,
  useColorModeValue,
  Container,
  Flex,
  HStack,
  IconButton,
  Progress,
  Spacer,
  Heading,
  Badge,
  SimpleGrid,
} from '@chakra-ui/react';
import { ChevronLeftIcon, ChevronRightIcon } from '@chakra-ui/icons';
import { motion } from 'framer-motion';
import { QuestionCard } from '../components/QuestionCard';
import { QuizResults } from '../components/QuizResults';
import { Question, QuizResult } from '../types';
import { submitQuiz, submitReview } from '../api';

interface QuizProps {
  questions: Question[];
  onReviewIncorrect: () => void;
  onRetakeQuiz: () => void;
  onBackToSets: () => void;
  isReview: boolean;
}

const parseOptions = (optionsStr: string | undefined | string[]): string[] => {
  if (!optionsStr) return [];
  
  // If it's already an array, return it
  if (Array.isArray(optionsStr)) {
    return optionsStr;
  }

  try {
    // Try to parse as JSON
    const parsed = JSON.parse(optionsStr);
    if (Array.isArray(parsed)) {
      return parsed;
    }
  } catch (error) {
    // If JSON parsing fails, try other methods
    if (typeof optionsStr === 'string') {
      // Check if it's a comma-separated string
      if (optionsStr.includes(',')) {
        return optionsStr.split(',').map(opt => opt.trim());
      }
      // If it's a single string, return it as a single-item array
      return [optionsStr];
    }
  }
  
  return [];
};

const MotionBox = motion(Box);
const MotionContainer = motion(Container);
const MotionButton = motion(Button);
const MotionFlex = motion(Flex);

export const Quiz: React.FC<QuizProps> = ({
  questions = [],
  onReviewIncorrect,
  onRetakeQuiz,
  onBackToSets,
  isReview,
}) => {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [timeElapsed, setTimeElapsed] = useState(0);
  const toast = useToast();

  const bgColor = useColorModeValue('gray.900', 'gray.900'); // #111111
  const cardBg = useColorModeValue('gray.800', 'gray.800'); // #1c1c1c
  const textColor = useColorModeValue('white', 'white');
  const buttonBg = useColorModeValue('blue.500', 'blue.500'); // #173150
  const buttonHoverBg = useColorModeValue('blue.600', 'blue.600'); // #132740
  const borderColor = useColorModeValue('gray.700', 'gray.700'); // #2a2a2a
  const badgeBg = useColorModeValue('gray.750', 'gray.750'); // #202020

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeElapsed(prev => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    // Reset state when questions change
    setAnswers({});
    setQuizResult(null);
    setCurrentQuestionIndex(0);
    setTimeElapsed(0);
  }, [questions]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleAnswerSelect = (questionId: number, answer: string) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: answer,
    }));
  };

  const handleSubmit = async () => {
    try {
      setIsSubmitting(true);
      const result = isReview ? 
        await submitReview(answers) : 
        await submitQuiz(answers);
      setQuizResult(result);
    } catch (error) {
      console.error('Error submitting quiz:', error);
      toast({
        title: 'Error',
        description: 'Failed to submit quiz. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (quizResult) {
    return (
      <QuizResults
        result={quizResult}
        onReviewIncorrect={onReviewIncorrect}
        onRetakeQuiz={onRetakeQuiz}
        onBackToSets={onBackToSets}
      />
    );
  }

  if (!Array.isArray(questions) || questions.length === 0) {
    return (
      <MotionContainer
        maxW="6xl"
        py={10}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <MotionBox
          bg={cardBg}
          p={8}
          borderRadius="xl"
          borderWidth="1px"
          borderColor={borderColor}
          textAlign="center"
          color={textColor}
        >
          <Heading size="lg" mb={6}>No Questions Available</Heading>
          <Text fontSize="lg" mb={8}>Please select a question set to begin the quiz.</Text>
          <MotionButton
            size="lg"
            bg={buttonBg}
            color={textColor}
            onClick={onBackToSets}
            _hover={{ bg: buttonHoverBg }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Back to Question Sets
          </MotionButton>
        </MotionBox>
      </MotionContainer>
    );
  }

  const currentQuestion = questions[currentQuestionIndex];
  const progress = (Object.keys(answers).length / questions.length) * 100;

  return (
    <MotionContainer
      maxW="6xl"
      py={8}
      px={4}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      position="relative"
    >
      <MotionFlex
        direction="column"
        spacing={8}
        align="stretch"
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header Section */}
        <Box 
          mb={8}
          bg={cardBg}
          p={6}
          borderRadius="xl"
          borderWidth="1px"
          borderColor={borderColor}
          boxShadow="lg"
        >
          <Flex justify="space-between" align="center" mb={4}>
            <HStack spacing={4}>
              <Badge
                colorScheme="blue"
                p={2}
                borderRadius="md"
                bg="gray.800"
                fontSize="sm"
                fontWeight="bold"
                border="1px solid"
                borderColor="blue.500"
                color="blue.100"
              >
                Trial 1 of 3
              </Badge>
              <Badge
                colorScheme="blue"
                p={2}
                borderRadius="md"
                bg="gray.800"
                fontSize="sm"
                fontWeight="bold"
                border="1px solid"
                borderColor="blue.500"
                color="blue.100"
              >
                {formatTime(timeElapsed)}
              </Badge>
            </HStack>
            <Badge
              colorScheme="blue"
              p={2}
              borderRadius="md"
              bg="gray.800"
              fontSize="sm"
              fontWeight="bold"
              border="1px solid"
              borderColor="blue.500"
              color="blue.100"
            >
              Question {currentQuestionIndex + 1} of {questions.length}
            </Badge>
          </Flex>

          <Box position="relative" mb={6}>
            <Progress
              value={progress}
              size="xs"
              colorScheme="blue"
              bg="gray.700"
              borderRadius="full"
              boxShadow="inner"
            />
          </Box>

          <Flex justify="center" wrap="wrap" gap={2}>
            {questions.map((_, index) => (
              <MotionBox
                key={index}
                as="button"
                w="35px"
                h="35px"
                borderRadius="full"
                bg={index === currentQuestionIndex ? 'blue.500' : 'gray.700'}
                color={textColor}
                display="flex"
                alignItems="center"
                justifyContent="center"
                cursor="pointer"
                onClick={() => setCurrentQuestionIndex(index)}
                transition="all 0.2s"
                whileHover={{ scale: 1.1, boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}
                whileTap={{ scale: 0.95 }}
                border={answers[questions[index].id] ? '2px solid' : 'none'}
                borderColor={answers[questions[index].id] ? 'blue.300' : undefined}
                boxShadow="md"
                _hover={{
                  bg: index === currentQuestionIndex ? 'blue.600' : 'gray.600',
                }}
              >
                {index + 1}
              </MotionBox>
            ))}
          </Flex>
        </Box>

        {/* Question Card */}
        <MotionBox
          bg={cardBg}
          borderRadius="xl"
          borderWidth="1px"
          borderColor={borderColor}
          overflow="hidden"
          mb={8}
          boxShadow="lg"
          whileHover={{ y: -2 }}
          transition={{ duration: 0.2 }}
        >
          <QuestionCard
            key={currentQuestion.id}
            questionId={currentQuestion.id}
            question={currentQuestion.question_text || ''}
            options={parseOptions(currentQuestion.options)}
            selectedAnswer={answers[currentQuestion.id]}
            onAnswerSelect={handleAnswerSelect}
            currentQuestionNumber={currentQuestionIndex + 1}
            totalQuestions={questions.length}
          />
        </MotionBox>

        {/* Navigation Controls */}
        <Flex 
          justify="space-between" 
          align="center" 
          mt={4}
          bg={cardBg}
          p={4}
          borderRadius="xl"
          borderWidth="1px"
          borderColor={borderColor}
          boxShadow="lg"
        >
          <IconButton
            aria-label="Previous question"
            icon={<ChevronLeftIcon boxSize={6} />}
            onClick={() => setCurrentQuestionIndex(prev => Math.max(0, prev - 1))}
            isDisabled={currentQuestionIndex === 0}
            size="lg"
            colorScheme="blue"
            variant="ghost"
            _hover={{ bg: 'blue.800' }}
          />

          <MotionButton
            colorScheme="blue"
            size="lg"
            minW="200px"
            onClick={currentQuestionIndex === questions.length - 1 ? handleSubmit : () => setCurrentQuestionIndex(prev => Math.min(questions.length - 1, prev + 1))}
            isLoading={isSubmitting}
            loadingText="Submitting..."
            whileHover={{ scale: 1.02, boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}
            whileTap={{ scale: 0.98 }}
            boxShadow="lg"
          >
            {currentQuestionIndex === questions.length - 1 ? 'Submit Quiz' : 'Next Question'}
          </MotionButton>

          <IconButton
            aria-label="Next question"
            icon={<ChevronRightIcon boxSize={6} />}
            onClick={() => setCurrentQuestionIndex(prev => Math.min(questions.length - 1, prev + 1))}
            isDisabled={currentQuestionIndex === questions.length - 1}
            size="lg"
            colorScheme="blue"
            variant="ghost"
            _hover={{ bg: 'blue.800' }}
          />
        </Flex>
      </MotionFlex>
    </MotionContainer>
  );
};
