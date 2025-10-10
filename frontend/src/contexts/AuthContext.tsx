import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import apiClient from '../services/apiClient';

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'end_user' | 'content_manager' | 'system_administrator';
  permissions: string[];
  lastLogin?: Date;
  token?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  updateUser: (userData: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Load user from backend API
    const loadUser = async () => {
      setIsLoading(true);
      try {
        // Fetch user info from backend
        const userInfo = await apiClient.getUserInfo();

        // Map backend user to frontend User type
        const mappedUser: User = {
          id: userInfo.uuid,
          username: userInfo.name || userInfo.email.split('@')[0],
          email: userInfo.email,
          role: userInfo.role === 'admin' ? 'system_administrator' : 'end_user',
          permissions: userInfo.role === 'admin'
            ? ['read', 'write', 'admin', 'agent_management', 'workflow_management']
            : ['read', 'write'],
          lastLogin: new Date()
        };

        setUser(mappedUser);
        // Store user ID in localStorage for backward compatibility
        localStorage.setItem('user_id', userInfo.uuid);
      } catch (error) {
        console.error('Failed to load user:', error);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    loadUser();
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    try {
      // Login is handled via OIDC redirect - this is just a placeholder
      // In a real implementation, this would redirect to the OIDC login page
      console.log('Login via OIDC not implemented in this context');
      return false;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  const updateUser = (userData: Partial<User>) => {
    if (user) {
      const updatedUser = { ...user, ...userData };
      setUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    updateUser
  };

  return (
    <AuthContext.Provider value={value}>
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

export default AuthContext;
