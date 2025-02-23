import React, { useState } from 'react';
import {
  Box,
  Button,
  VStack,
  useToast,
  Progress,
  Text,
  useColorModeValue,
} from '@chakra-ui/react';
import { QuestionCard } from '../components/QuestionCard';
import { QuizResults } from '../components/QuizResults';
import { Question, ReviewResult } from '../types';
import { submitReview } from '../api';

interface ReviewProps {
  incorrectQuestions: Question[];
  onFinishReview: () => void;
}

export const Review: React.FC<ReviewProps> = ({
  incorrectQuestions,
  onFinishReview,
}) => {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);
  const toast = useToast();

  const bgColor = useColorModeValue('gray.100', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const handleAnswerSelect = (questionId: number, answer: string) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: answer,
    }));
  };

  const handleSubmit = async () => {
    if (Object.keys(answers).length < incorrectQuestions.length) {
      toast({
        title: 'Incomplete Review',
        description: 'Please answer all questions before submitting',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    try {
      setIsSubmitting(true);
      const result = await submitReview(answers);
      setReviewResult(result);
    } catch (error) {
      toast({
        title: 'Error submitting review',
        description: 'Please try again',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (reviewResult) {
    return (
      <QuizResults
        result={reviewResult}
        onReviewIncorrect={() => {
          // Reset state and start over with incorrect answers
          setAnswers({});
          setReviewResult(null);
        }}
        onRetakeQuiz={onFinishReview}
        onBackToSets={() => {
          window.location.reload();
        }}
      />
    );
  }

  return (
    <Box maxW="800px" mx="auto" p={6}>
      <VStack spacing={6} align="stretch">
        <Box
          p={6}
          bg={bgColor}
          borderRadius="lg"
          borderWidth="1px"
          borderColor={borderColor}
        >
          <Text mb={4} fontSize="lg" fontWeight="medium">
            Review Progress: {Object.keys(answers).length} /{' '}
            {incorrectQuestions.length} questions answered
          </Text>
          <Progress
            value={(Object.keys(answers).length / incorrectQuestions.length) * 100}
            size="sm"
            colorScheme="blue"
            borderRadius="full"
          />
        </Box>

        {incorrectQuestions.map((question) => (
          <QuestionCard
            key={question.id}
            questionId={question.id}
            question={question.question}
            options={question.options}
            selectedAnswer={answers[question.id]}
            onAnswerSelect={handleAnswerSelect}
          />
        ))}

        <Button
          colorScheme="green"
          size="lg"
          onClick={handleSubmit}
          isLoading={isSubmitting}
          loadingText="Submitting..."
        >
          Submit Review
        </Button>
      </VStack>
    </Box>
  );
};
