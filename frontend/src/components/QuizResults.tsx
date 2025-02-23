import React from 'react';
import {
  Box,
  Button,
  VStack,
  Text,
  useColorModeValue,
  Container,
  Heading,
  CircularProgress,
  CircularProgressLabel,
  HStack,
  Icon,
  Flex,
  Divider,
  Badge,
} from '@chakra-ui/react';
import {
  CheckCircleIcon,
  RepeatIcon,
  ViewIcon,
  ArrowBackIcon,
} from '@chakra-ui/icons';
import { motion } from 'framer-motion';
import { QuizResult } from '../types';

interface QuizResultsProps {
  result: QuizResult;
  onReviewIncorrect: () => void;
  onRetakeQuiz: () => void;
  onBackToSets: () => void;
}

const MotionBox = motion(Box);
const MotionContainer = motion(Container);
const MotionButton = motion(Button);
const MotionFlex = motion(Flex);

export const QuizResults: React.FC<QuizResultsProps> = ({
  result,
  onReviewIncorrect,
  onRetakeQuiz,
  onBackToSets,
}) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const scoreColor = useColorModeValue('blue.600', 'blue.300');
  const statBg = useColorModeValue('blue.50', 'blue.900');

  // Add null check for result
  if (!result) {
    return (
      <Container maxW="4xl" py={10}>
        <VStack spacing={8} align="stretch">
          <Box bg={bgColor} p={8} borderRadius="xl" textAlign="center">
            <Heading size="lg" mb={2}>Error Loading Results</Heading>
            <Text>Unable to load quiz results. Please try again.</Text>
            <Button onClick={onBackToSets} mt={4}>Back to Question Sets</Button>
          </Box>
        </VStack>
      </Container>
    );
  }

  const percentage = Math.round((result.score / result.total) * 100);
  const incorrectCount = Object.keys(result.incorrect_answers || {}).length;

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'green';
    if (score >= 60) return 'yellow';
    return 'red';
  };

  const scoreColorScheme = getScoreColor(percentage);

  const handleReviewClick = () => {
    console.log('Review button clicked');
    onReviewIncorrect();
  };

  return (
    <Container maxW="4xl" py={10}>
      <VStack spacing={8} align="stretch">
        <MotionBox
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Box
            bg={bgColor}
            p={8}
            borderRadius="xl"
            boxShadow="xl"
            border="1px"
            borderColor={borderColor}
          >
            <VStack spacing={6}>
              <Heading size="xl" mb={2}>
                Quiz Results
              </Heading>

              <Box
                w="full"
                h="4px"
                bg={`${scoreColorScheme}.200`}
                borderRadius="full"
                position="relative"
                mt={4}
              >
                <Box
                  position="absolute"
                  h="full"
                  w={`${percentage}%`}
                  bg={`${scoreColorScheme}.500`}
                  borderRadius="full"
                  transition="width 1s ease-in-out"
                />
              </Box>

              <Text fontSize="2xl" fontWeight="bold" color={`${scoreColorScheme}.500`}>
                {percentage}% Score
              </Text>

              <HStack spacing={8} justify="center" w="full" p={4} bg={statBg} borderRadius="lg">
                <MotionFlex
                  direction="column"
                  align="center"
                  variants={{
                    hidden: { opacity: 0, y: 20 },
                    visible: { opacity: 1, y: 0 }
                  }}
                  transition={{ delay: 0.5, duration: 0.5 }}
                >
                  <Icon as={CheckCircleIcon} w={8} h={8} color="green.400" mb={2} />
                  <Text fontSize="2xl" fontWeight="bold" color="green.400">
                    {result.score}
                  </Text>
                  <Text fontSize="sm" color="gray.500">
                    Correct
                  </Text>
                </MotionFlex>

                <Divider orientation="vertical" height="80px" />

                <MotionFlex
                  direction="column"
                  align="center"
                  variants={{
                    hidden: { opacity: 0, y: 20 },
                    visible: { opacity: 1, y: 0 }
                  }}
                  transition={{ delay: 0.7, duration: 0.5 }}
                >
                  <Icon as={ViewIcon} w={8} h={8} color="red.400" mb={2} />
                  <Text fontSize="2xl" fontWeight="bold" color="red.400">
                    {incorrectCount}
                  </Text>
                  <Text fontSize="sm" color="gray.500">
                    Incorrect
                  </Text>
                </MotionFlex>
              </HStack>

              {incorrectCount > 0 && (
                <Badge
                  colorScheme="blue"
                  p={2}
                  borderRadius="lg"
                  textAlign="center"
                  fontSize="sm"
                >
                  You can review incorrect answers to improve your score
                </Badge>
              )}

              <VStack spacing={4} width="full">
                {incorrectCount > 0 && (
                  <MotionButton
                    leftIcon={<ViewIcon />}
                    colorScheme="blue"
                    size="lg"
                    onClick={handleReviewClick}
                    width="full"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    Review Incorrect Answers
                  </MotionButton>
                )}

                <MotionButton
                  leftIcon={<RepeatIcon />}
                  colorScheme="green"
                  size="lg"
                  onClick={onRetakeQuiz}
                  width="full"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Retake Quiz
                </MotionButton>

                <MotionButton
                  leftIcon={<ArrowBackIcon />}
                  variant="outline"
                  size="lg"
                  onClick={onBackToSets}
                  width="full"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Back to Question Sets
                </MotionButton>
              </VStack>
            </VStack>
          </Box>
        </MotionBox>
      </VStack>
    </Container>
  );
};
