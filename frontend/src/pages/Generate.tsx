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
  Text,
  Container,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Alert,
  AlertIcon,
  AlertDescription,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { useQueryClient } from '@tanstack/react-query';
import { uploadQuestions, getUploadProgress } from '../api';

const MotionBox = motion(Box);
const MotionButton = motion(Button);

export const Generate: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [setName, setSetName] = useState('');
  const [numQuestions, setNumQuestions] = useState<number>(10);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState('');

  const toast = useToast();
  const queryClient = useQueryClient();

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files;
    if (selectedFiles) {
      setFiles(Array.from(selectedFiles));
    }
  };

  const handleGenerate = async () => {
    if (files.length === 0) {
      toast({
        title: 'No files selected',
        description: 'Please select at least one lecture file to upload.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (!setName) {
      toast({
        title: 'Set name required',
        description: 'Please enter a name for this question set.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsGenerating(true);
    setGenerationStatus('Uploading files...');

    try {
      const formData = new FormData();
      formData.append('file', files[0]); // Currently only supporting one file
      formData.append('set_name', setName);
      formData.append('num_questions', numQuestions.toString());

      const response = await uploadQuestions(formData);
      
      if (response.session_id) {
        // Start polling for progress
        let retryCount = 0;
        const maxRetries = 120; // Maximum 2 minutes of polling
        
        const pollInterval = setInterval(async () => {
          try {
            if (retryCount >= maxRetries) {
              clearInterval(pollInterval);
              throw new Error('Generation timed out');
            }

            const progress = await getUploadProgress(response.session_id);
            
            // Update status
            if (progress.message) {
              setGenerationStatus(progress.message);
            }
            
            // Check for completion or error
            if (progress.status === 'complete') {
              clearInterval(pollInterval);
              queryClient.invalidateQueries(['questionSets']);
              setFiles([]);
              setSetName('');
              setNumQuestions(10);
              toast({
                title: 'Success!',
                description: progress.message,
                status: 'success',
                duration: 3000,
                isClosable: true,
              });
              setIsGenerating(false);
              setGenerationStatus('');
            } else if (progress.status === 'error') {
              clearInterval(pollInterval);
              throw new Error(progress.message || 'Failed to generate questions');
            }
            
            retryCount++;
          } catch (error) {
            clearInterval(pollInterval);
            throw error;
          }
        }, 1000);
      } else {
        // If no session_id, assume direct completion
        queryClient.invalidateQueries(['questionSets']);
        setFiles([]);
        setSetName('');
        setNumQuestions(10);
        toast({
          title: 'Success!',
          description: response.message,
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to generate questions. Please try again.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsGenerating(false);
      setGenerationStatus('');
    }
  };

  return (
    <Container maxW="container.xl" py={8}>
      <MotionBox
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <VStack spacing={8} align="stretch">
          <Heading size="xl" textAlign="center" color="blue.500">
            Generate MCQ Questions
          </Heading>

          <Box
            p={8}
            borderWidth={2}
            borderRadius="xl"
            borderStyle="dashed"
            borderColor="blue.200"
            bg="gray.800"
          >
            <VStack spacing={6}>
              <FormControl>
                <FormLabel>Question Set Name</FormLabel>
                <Input
                  value={setName}
                  onChange={(e) => setSetName(e.target.value)}
                  placeholder="Enter a name for this question set"
                  size="lg"
                />
              </FormControl>

              <FormControl>
                <FormLabel>Number of Questions to Generate</FormLabel>
                <NumberInput
                  value={numQuestions}
                  onChange={(_, value) => setNumQuestions(value)}
                  min={1}
                  max={50}
                  size="lg"
                >
                  <NumberInputField />
                  <NumberInputStepper>
                    <NumberIncrementStepper />
                    <NumberDecrementStepper />
                  </NumberInputStepper>
                </NumberInput>
              </FormControl>

              <FormControl>
                <FormLabel>Upload Lecture Files (PDF)</FormLabel>
                <Input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  multiple
                  size="lg"
                  p={2}
                />
              </FormControl>

              {files.length > 0 && (
                <Box w="100%">
                  <Text mb={2} fontWeight="bold">Selected Files:</Text>
                  <VStack align="start" spacing={1}>
                    {files.map((file, index) => (
                      <Text key={index} fontSize="sm">{file.name}</Text>
                    ))}
                  </VStack>
                </Box>
              )}

              <MotionButton
                colorScheme="blue"
                size="lg"
                width="100%"
                onClick={handleGenerate}
                isLoading={isGenerating}
                loadingText="Generating Questions..."
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Generate MCQ Questions
              </MotionButton>

              {generationStatus && (
                <Alert status="info" variant="left-accent">
                  <AlertIcon />
                  <AlertDescription>{generationStatus}</AlertDescription>
                </Alert>
              )}
            </VStack>
          </Box>
        </VStack>
      </MotionBox>
    </Container>
  );
};

export default Generate;
