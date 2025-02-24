import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  Input,
  VStack,
  Text,
  Container,
  InputGroup,
  InputLeftElement,
  Link,
  useToast,
} from '@chakra-ui/react';
import { DoorOpen } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api/auth';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';

const MotionBox = motion(Box);

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const toast = useToast();
  const { setUser } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await login(username, password);
      localStorage.setItem('token', response.access_token);
      setUser(response.user);
      navigate('/dashboard');
    } catch (err: any) {
      toast({
        title: 'Error',
        description: err.response?.data?.error || 'Invalid username or password',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      minH="100vh"
      bg="linear-gradient(135deg, #010203 50%, #1c0607 100%)"
      py={20}
      display="flex"
      alignItems="center"
      justifyContent="center"
    >
      <Container maxW="md">
        <MotionBox
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Box
            p={8}
            bg="rgba(30, 30, 17, 0.9)"
            backdropFilter="blur(10px)"
            borderRadius="24px"
            border="1px solid"
            borderColor="whiteAlpha.200"
            boxShadow="xl"
          >
            <VStack spacing={6} align="stretch">
              <VStack spacing={2}>
                <Box
                  bg="whiteAlpha.200"
                  p={3}
                  borderRadius="full"
                  width="48px"
                  height="48px"
                  display="flex"
                  alignItems="center"
                  justifyContent="center"
                >
                  <DoorOpen color="white" boxSize={6} />
                </Box>
                <Text
                  fontSize="2xl"
                  fontWeight="bold"
                  color="white"
                  textAlign="center"
                >
                  Welcome Back!
                </Text>
                <Text color="whiteAlpha.600" textAlign="center" fontSize="sm">
                  Please sign in to continue
                </Text>
              </VStack>

              <form onSubmit={handleSubmit} style={{ width: '100%' }}>
                <VStack spacing={4}>
                  <FormControl>
                    <InputGroup>
                      <Input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="Username"
                        size="lg"
                        bg="whiteAlpha.100"
                        border="none"
                        color="white"
                        _placeholder={{ color: 'whiteAlpha.500' }}
                        _hover={{ bg: 'whiteAlpha.200' }}
                        _focus={{ bg: 'whiteAlpha.200', boxShadow: 'none' }}
                        height="56px"
                        borderRadius="16px"
                      />
                    </InputGroup>
                  </FormControl>

                  <FormControl>
                    <InputGroup>
                      <Input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Password"
                        size="lg"
                        bg="whiteAlpha.100"
                        border="none"
                        color="white"
                        _placeholder={{ color: 'whiteAlpha.500' }}
                        _hover={{ bg: 'whiteAlpha.200' }}
                        _focus={{ bg: 'whiteAlpha.200', boxShadow: 'none' }}
                        height="56px"
                        borderRadius="16px"
                      />
                    </InputGroup>
                  </FormControl>

                  <Button
                    type="submit"
                    width="100%"
                    height="56px"
                    isLoading={loading}
                    loadingText="Signing in..."
                    bg="whiteAlpha.900"
                    color="black"
                    _hover={{ bg: 'whiteAlpha.800' }}
                    _active={{ bg: 'whiteAlpha.700' }}
                    borderRadius="16px"
                    fontSize="md"
                    fontWeight="semibold"
                    boxShadow="lg"
                  >
                    Get Started
                  </Button>
                </VStack>
              </form>
            </VStack>
          </Box>
        </MotionBox>
      </Container>
    </Box>
  );
};

export default Login;
