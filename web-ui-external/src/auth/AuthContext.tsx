import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import client from '../api/client';

interface User {
  email: string;
  role: string;
  id?: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
  login: (email: string, password?: string) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize from local storage
  useEffect(() => {
    const initAuth = () => {
      const token = localStorage.getItem('auth_token');
      const savedUser = localStorage.getItem('auth_user');

      if (token) {
        setIsAuthenticated(true);
        if (savedUser) {
          try {
            setUser(JSON.parse(savedUser));
          } catch (e) {
            console.error('Failed to parse saved user', e);
          }
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email: string, password?: string) => {
    // Phase 02.1 specifies Email/Password token exchange via /api/auth/token
    // For password auth, it uses x-api-key or standard form data depending on backend config
    // In our spec, we pass x-api-key for Email/Password if password is provided
    try {
      const response = await client.post('/auth/token', null, {
        headers: password ? { 'x-api-key': password } : {}
      });

      const { access_token } = response.data;
      if (!access_token) throw new Error('No access token received');

      localStorage.setItem('auth_token', access_token);

      // We would ideally get user details from the token or another endpoint
      // For now, mock it based on email
      const userData = { email, role: 'user' };
      localStorage.setItem('auth_user', JSON.stringify(userData));

      setIsAuthenticated(true);
      setUser(userData);
    } catch (error) {
      console.error('Login failed', error);
      throw error;
    }
  };

  const loginWithGoogle = async (credential: string) => {
    try {
      // D-05: Google OAuth via GIS SDK, token exchange with backend
      const response = await client.post('/auth/google', { token: credential });

      const { access_token } = response.data;
      if (!access_token) throw new Error('No access token received');

      localStorage.setItem('auth_token', access_token);

      // Decode JWT to get user info, or get from backend response
      // Mocking for now as the backend should ideally return this
      const userData = { email: 'google-user@example.com', role: 'user' };
      localStorage.setItem('auth_user', JSON.stringify(userData));

      setIsAuthenticated(true);
      setUser(userData);
    } catch (error) {
      console.error('Google login failed', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    setIsAuthenticated(false);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, isLoading, login, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};