import React from 'react';
import {
  Box,
  Radio,
  RadioGroup,
  Stack,
  Text,
  useColorModeValue,
  VStack,
  Flex,
  Circle,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';

interface QuestionCardProps {
  questionId: number;
  question: string;
  options: string[];
  selectedAnswer?: string;
  correctAnswer?: string;
  isDisabled?: boolean;
  onAnswerSelect: (questionId: number, answer: string) => void;
  currentQuestionNumber: number;
  totalQuestions: number;
}

const MotionBox = motion(Box);

const alphabet = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];

export const QuestionCard: React.FC<QuestionCardProps> = ({
  questionId,
  question,
  options = [],
  selectedAnswer,
  correctAnswer,
  isDisabled = false,
  onAnswerSelect,
  currentQuestionNumber,
  totalQuestions,
}) => {
  const bgColor = useColorModeValue('gray.800', 'gray.900');
  const textColor = useColorModeValue('gray.100', 'gray.50');
  const optionBg = useColorModeValue('gray.700', 'gray.800');
  const optionHoverBg = useColorModeValue('gray.600', 'gray.700');
  const selectedBg = useColorModeValue('blue.500', 'blue.600');
  const circleBg = useColorModeValue('gray.700', 'gray.800');
  const circleColor = useColorModeValue('gray.300', 'gray.200');

  if (!question || !Array.isArray(options)) {
    return null;
  }

  return (
    <MotionBox
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      bg={bgColor}
      borderRadius="xl"
      p={6}
      color={textColor}
      position="relative"
    >
      <VStack align="stretch" spacing={6}>
        <Flex justify="space-between" align="center" mb={4}>
          <Text fontSize="sm" color="gray.400">
            Question {currentQuestionNumber} of {totalQuestions}
          </Text>
        </Flex>

        <Text fontSize="lg" fontWeight="medium" mb={6}>
          {question}
        </Text>

        <RadioGroup
          value={selectedAnswer}
          onChange={(value) => onAnswerSelect(questionId, value)}
          isDisabled={isDisabled}
        >
          <Stack spacing={4}>
            {options.map((option, index) => (
              <MotionBox
                key={index}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
              >
                <Box
                  as="label"
                  display="flex"
                  alignItems="center"
                  p={4}
                  bg={selectedAnswer === option ? selectedBg : optionBg}
                  borderRadius="lg"
                  cursor={isDisabled ? 'not-allowed' : 'pointer'}
                  transition="all 0.2s"
                  _hover={!isDisabled && selectedAnswer !== option ? { bg: optionHoverBg } : {}}
                >
                  <Circle
                    size="30px"
                    bg={circleBg}
                    color={circleColor}
                    mr={4}
                    fontSize="sm"
                    fontWeight="bold"
                  >
                    {alphabet[index]}
                  </Circle>
                  <Radio
                    value={option}
                    isDisabled={isDisabled}
                    colorScheme="blue"
                    sx={{
                      '[data-checked]': {
                        bg: 'blue.200',
                        borderColor: 'blue.200',
                      },
                    }}
                  >
                    <Text ml={2}>{option}</Text>
                  </Radio>
                </Box>
              </MotionBox>
            ))}
          </Stack>
        </RadioGroup>
      </VStack>
    </MotionBox>
  );
};
