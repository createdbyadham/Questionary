import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  Heading,
  useToast,
  Progress,
  Text,
  Grid,
  IconButton,
  HStack,
  useColorModeValue,
  Container,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Portal,
  Alert,
  AlertIcon,
  AlertDescription,
} from '@chakra-ui/react';
import { DeleteIcon, EditIcon, ChevronDownIcon } from '@chakra-ui/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Question, QuestionSet } from '../types';
import { getQuestionSets, startQuiz, deleteSet, updateSetName, uploadQuestions, getUploadProgress } from '../api';
import { motion } from 'framer-motion';

const MotionBox = motion(Box);
const MotionButton = motion(Button);

interface HomeProps {
  onStartQuiz: (questions: Question[]) => void;
}

export const Home: React.FC<HomeProps> = ({ onStartQuiz }) => {
  const [file, setFile] = useState<File | null>(null);
  const [setName, setSetName] = useState('');
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [selectedSets, setSelectedSets] = useState<number[]>([]);
  const [editingSetId, setEditingSetId] = useState<number | null>(null);
  const [newSetName, setNewSetName] = useState('');
  const [isStartingQuiz, setIsStartingQuiz] = useState(false);

  const toast = useToast();
  const queryClient = useQueryClient();
  
  // Updated color scheme
  const bgColor = useColorModeValue('gray.800', 'gray.800');
  const cardBg = useColorModeValue('gray.700', 'gray.700');
  const borderColor = useColorModeValue('gray.600', 'gray.600');
  const textColor = useColorModeValue('white', 'white');
  const buttonBg = useColorModeValue('blue.500', 'blue.500');
  const buttonHoverBg = useColorModeValue('blue.600', 'blue.600');

  const { data: questionSets, isLoading, error } = useQuery<QuestionSet[]>({
    queryKey: ['questionSets'],
    queryFn: getQuestionSets,
  });

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setFile(event.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      toast({
        title: 'No file selected',
        description: 'Please select a file to upload',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    try {
      setUploadProgress(0);
      setUploadStatus('Starting upload...');
      const response = await uploadQuestions(file, setName);
      
      // If it's a JSON file, we'll get questions_imported in the response
      if ('questions_imported' in response) {
        toast({
          title: 'Upload successful',
          description: response.message,
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        queryClient.invalidateQueries({ queryKey: ['questionSets'] });
        setFile(null);
        setSetName('');
        setUploadProgress(null);
        setUploadStatus('');
        return;
      }
      
      // For PDF files, handle progress tracking
      if (!response.session_id) {
        throw new Error('No session ID received from server');
      }

      let retryCount = 0;
      const maxRetries = 120; // Maximum 2 minutes of polling
      
      // Start polling for progress
      const pollInterval = setInterval(async () => {
        try {
          if (retryCount >= maxRetries) {
            clearInterval(pollInterval);
            throw new Error('Upload timed out');
          }

          const progress = await getUploadProgress(response.session_id!);
          
          // Update progress and status
          if (progress.percent !== undefined) {
            setUploadProgress(progress.percent);
          }
          if (progress.message) {
            setUploadStatus(progress.message);
          }
          
          // Check for completion or error
          if (progress.status === 'complete') {
            clearInterval(pollInterval);
            toast({
              title: 'Upload successful',
              description: progress.message,
              status: 'success',
              duration: 3000,
              isClosable: true,
            });
            // Add a small delay before invalidating queries to ensure DB consistency
            setTimeout(() => {
              queryClient.invalidateQueries({ queryKey: ['questionSets'] });
            }, 500);
            setFile(null);
            setSetName('');
            setUploadProgress(null);
            setUploadStatus('');
          } else if (progress.status === 'error') {
            clearInterval(pollInterval);
            throw new Error(progress.message || 'Upload failed');
          }
          
          retryCount++;
        } catch (error) {
          clearInterval(pollInterval);
          throw error;
        }
      }, 1000); // Check every second
    } catch (error) {
      setUploadProgress(null);
      setUploadStatus('');
      toast({
        title: 'Upload failed',
        description: error instanceof Error ? error.message : 'An error occurred',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleStartQuiz = async () => {
    if (selectedSets.length === 0) {
      toast({
        title: 'No sets selected',
        description: 'Please select at least one question set',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    try {
      setIsStartingQuiz(true);
      const questions = await startQuiz(selectedSets);
      if (questions.length === 0) {
        toast({
          title: 'No questions available',
          description: 'The selected sets contain no questions',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
        return;
      }
      onStartQuiz(questions);
    } catch (error) {
      console.error('Error starting quiz:', error);
      toast({
        title: 'Error',
        description: 'Failed to start quiz. Please try again.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsStartingQuiz(false);
    }
  };

  const handleDeleteSet = async (setId: number) => {
    try {
      await deleteSet(setId);
      queryClient.invalidateQueries({ queryKey: ['questionSets'] });
      toast({
        title: 'Success',
        description: 'Question set deleted',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete question set',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleUpdateSetName = async (setId: number, newName: string) => {
    try {
      await updateSetName(setId, newName);
      queryClient.invalidateQueries({ queryKey: ['questionSets'] });
      setEditingSetId(null);
      toast({
        title: 'Success',
        description: 'Question set name updated',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update set name',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const toggleSetSelection = (setId: number) => {
    setSelectedSets((prev) =>
      prev.includes(setId)
        ? prev.filter((id) => id !== setId)
        : [...prev, setId]
    );
  };

  const handleSetSelection = (setId: number) => {
    toggleSetSelection(setId);
    // Provide haptic feedback
    const feedback = selectedSets.includes(setId) ? 'Selected' : 'Unselected';
    toast({
      title: feedback,
      description: `Question set ${feedback.toLowerCase()}`,
      status: 'info',
      duration: 1000,
      isClosable: true,
      position: 'bottom-right',
    });
  };

  const handleEditSetName = (setId: number, setName: string) => {
    setEditingSetId(setId);
    setNewSetName(setName);
  };

  if (isLoading) {
    return (
      <Box minH="100vh" bg="gray.900" py={8}>
        <Container maxW="container.lg">
          <VStack spacing={8}>
            <Heading color={textColor} size={{ base: "lg", md: "xl" }} textAlign="center">
              Questionary
            </Heading>
            <Grid
              templateColumns={{
                base: "repeat(1, 1fr)",
                sm: "repeat(2, 1fr)",
                md: "repeat(3, 1fr)",
                lg: "repeat(4, 1fr)"
              }}
              gap={4}
              w="full"
            >
              {[...Array(8)].map((_, i) => (
                <MotionBox
                  key={i}
                  height="120px"
                  bg="gray.800"
                  borderRadius="lg"
                  animate={{ opacity: [0.3, 0.7, 0.3] }}
                  transition={{ repeat: Infinity, duration: 1.5 }}
                />
              ))}
            </Grid>
          </VStack>
        </Container>
      </Box>
    );
  }

  if (error) {
    return (
      <Box minH="100vh" bg="gray.900" py={8}>
        <Container maxW="container.lg">
          <VStack spacing={8}>
            <Heading color={textColor} size={{ base: "lg", md: "xl" }} textAlign="center">
              Questionary
            </Heading>
            <Box
              bg="red.900"
              p={6}
              borderRadius="xl"
              borderColor="red.500"
              border="1px solid"
            >
              <VStack spacing={4}>
                <Text color="white">Failed to load question sets</Text>
                <Button
                  onClick={() => queryClient.invalidateQueries({ queryKey: ['questionSets'] })}
                  colorScheme="red"
                >
                  Retry
                </Button>
              </VStack>
            </Box>
          </VStack>
        </Container>
      </Box>
    );
  }

  return (
    <Box
      minH="100vh"
      bg="gray.900"
      py={8}
      position="relative"
    >
      <Box
        position="absolute"
        top="0"
        left="0"
        right="0"
        bottom="0"
        bgImage="radial-gradient(circle at 50% 50%, rgba(23, 49, 80, 0.08) 0%, rgba(17, 17, 17, 0) 70%)"
        pointerEvents="none"
      />
      <Container maxW="container.lg" position="relative" px={{ base: 4, md: 8 }}>
        <VStack spacing={{ base: 6, md: 8 }} align="stretch">
          <Heading color={textColor} size={{ base: "lg", md: "xl" }} textAlign="center" mb={{ base: 6, md: 8 }}>
            Questionary
          </Heading>

          <MotionBox
            bg={bgColor}
            p={{ base: 4, md: 6 }}
            borderRadius="xl"
            boxShadow="xl"
            border="1px solid"
            borderColor={borderColor}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <VStack spacing={4}>
              <FormControl>
                <FormLabel color={textColor}>Set Name</FormLabel>
                <Input
                  value={setName}
                  onChange={(e) => setSetName(e.target.value)}
                  placeholder="Enter set name"
                  bg="gray.800"
                  border="1px solid"
                  borderColor={borderColor}
                  color={textColor}
                  _placeholder={{ color: 'gray.400' }}
                  _hover={{ borderColor: 'blue.400' }}
                  _focus={{ borderColor: 'blue.500', boxShadow: 'none' }}
                />
              </FormControl>

              <FormControl>
                <FormLabel color={textColor}>Upload File</FormLabel>
                <Box position="relative">
                  <Input
                    type="file"
                    accept=".pdf, .json"
                    onChange={handleFileChange}
                    height="40px"
                    padding="0"
                    border="2px dashed"
                    borderColor={file ? 'blue.500' : borderColor}
                    bg="gray.800"
                    color={textColor}
                    _hover={{ borderColor: 'blue.400' }}
                    sx={{
                      '&::file-selector-button': {
                        height: '100%',
                        padding: '0 20px',
                        background: file ? 'blue.500' : 'gray.700',
                        border: 'none',
                        borderRight: '2px dashed',
                        borderColor: file ? 'blue.500' : borderColor,
                        color: textColor,
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        _hover: {
                          bg: 'blue.600'
                        }
                      }
                    }}
                  />
                  {file && (
                    <Text
                      position="absolute"
                      right="12px"
                      top="50%"
                      transform="translateY(-50%)"
                      fontSize="sm"
                      color="blue.200"
                    >
                      {file.name}
                    </Text>
                  )}
                </Box>
              </FormControl>

              <MotionButton
                colorScheme="blue"
                onClick={handleUpload}
                isLoading={uploadProgress !== null}
                loadingText="Uploading..."
                w="full"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Upload File
              </MotionButton>

              {uploadProgress !== null && (
                <Box>
                  <Progress value={uploadProgress} size="sm" colorScheme="blue" mb={2} />
                  <Alert status={uploadProgress === 100 ? 'success' : 'info'} variant="left-accent">
                    <AlertIcon />
                    <AlertDescription>{uploadStatus || 'Processing...'}</AlertDescription>
                  </Alert>
                </Box>
              )}
            </VStack>
          </MotionBox>

          <MotionBox
            bg={bgColor}
            p={{ base: 4, md: 6 }}
            borderRadius="xl"
            boxShadow="xl"
            border="1px solid"
            borderColor={borderColor}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
          >
            <VStack spacing={4} align="stretch">
              <HStack spacing={4} justify="space-between" mb={4}>
                <Heading size={{ base: "md", md: "lg" }} color={textColor}>
                  Question Sets
                </Heading>
                {selectedSets.length > 0 && (
                  <Box
                    bg="blue.500"
                    color="white"
                    px={3}
                    py={1}
                    borderRadius="full"
                    fontSize="sm"
                    fontWeight="medium"
                  >
                    {selectedSets.length} Selected
                  </Box>
                )}
              </HStack>

              <Grid 
                templateColumns={{
                  base: "repeat(1, 1fr)",
                  sm: "repeat(2, 1fr)",
                  md: "repeat(3, 1fr)",
                  lg: "repeat(4, 1fr)"
                }}
                gap={4}
              >
                {questionSets?.map((set) => (
                  <MotionBox
                    key={set.id}
                    bg={cardBg}
                    p={4}
                    borderRadius="lg"
                    border="1px solid"
                    borderColor={selectedSets.includes(set.id) ? 'blue.400' : borderColor}
                    cursor="pointer"
                    onClick={() => handleSetSelection(set.id)}
                    position="relative"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    initial={{ opacity: 0 }}
                    animate={{ 
                      opacity: 1,
                      boxShadow: selectedSets.includes(set.id) ? '0 0 0 2px rgba(66, 153, 225, 0.3)' : 'none'
                    }}
                    _hover={{ borderColor: 'blue.400' }}
                    style={{ zIndex: 1 }}
                    role="button"
                    tabIndex={0}
                    aria-pressed={selectedSets.includes(set.id)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSetSelection(set.id)}
                    _focus={{ boxShadow: 'outline', borderColor: 'blue.400' }}
                  >
                    {selectedSets.includes(set.id) && (
                      <Box
                        position="absolute"
                        top={5}
                        right={10}
                        bg="blue.400"
                        borderRadius="full"
                        w={2}
                        h={2}
                        animation="pulse 2s infinite"
                        sx={{
                          '@keyframes pulse': {
                            '0%': { transform: 'scale(0.95)', boxShadow: '0 0 0 0 rgba(66, 153, 225, 0.7)' },
                            '70%': { transform: 'scale(1)', boxShadow: '0 0 0 6px rgba(66, 153, 225, 0)' },
                            '100%': { transform: 'scale(0.95)', boxShadow: '0 0 0 0 rgba(66, 153, 225, 0)' }
                          }
                        }}
                      />
                    )}
                    {editingSetId === set.id ? (
                      <Input
                        value={newSetName}
                        onChange={(e) => setNewSetName(e.target.value)}
                        onBlur={() => handleUpdateSetName(set.id, newSetName)}
                        onKeyPress={(e) => e.key === 'Enter' && handleUpdateSetName(set.id, newSetName)}
                        autoFocus
                        bg="gray.800"
                        color={textColor}
                        borderColor={borderColor}
                        aria-label="Edit set name"
                      />
                    ) : (
                      <>
                        <Text color={textColor} fontWeight="medium">
                          {set.name}
                        </Text>
                        <Text color="gray.400" fontSize="sm" aria-label={`Contains ${set.question_count} questions`}>
                          {set.question_count} questions
                        </Text>
                        <Box position="absolute" top={2} right={2} zIndex={2}>
                          <Menu isLazy>
                            <MenuButton
                              as={IconButton}
                              icon={<ChevronDownIcon />}
                              variant="ghost"
                              size="sm"
                              color="gray.400"
                              _hover={{ color: 'white', bg: 'gray.700' }}
                              onClick={(e) => e.stopPropagation()}
                              aria-label="Question set options"
                            />
                            <Portal>
                              <MenuList
                                bg="gray.800"
                                borderColor="gray.700"
                                boxShadow="dark-lg"
                                onClick={(e) => e.stopPropagation()}
                                borderRadius="xl"
                                overflow="hidden"
                                py={2}
                              >
                                <MenuItem
                                  icon={<EditIcon />}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleEditSetName(set.id, set.name);
                                  }}
                                  _hover={{ bg: 'gray.700' }}
                                  bg="gray.800"
                                  color="gray.100"
                                  fontSize="sm"
                                >
                                  Edit Name
                                </MenuItem>
                                <MenuItem
                                  icon={<DeleteIcon />}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteSet(set.id);
                                  }}
                                  _hover={{ bg: 'red.800' }}
                                  bg="gray.800"
                                  color="red.300"
                                  fontSize="sm"
                                >
                                  Delete Set
                                </MenuItem>
                              </MenuList>
                            </Portal>
                          </Menu>
                        </Box>
                      </>
                    )}
                  </MotionBox>
                ))}
              </Grid>

              <MotionButton
                colorScheme="blue"
                size="lg"
                onClick={handleStartQuiz}
                isLoading={isStartingQuiz}
                loadingText="Starting Quiz..."
                isDisabled={selectedSets.length === 0}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Start Quiz ({selectedSets.length} sets selected)
              </MotionButton>
            </VStack>
          </MotionBox>
        </VStack>
      </Container>
    </Box>
  );
};
