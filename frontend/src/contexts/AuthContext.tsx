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
  error: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  updateUser: (userData: Partial<User>) => void;
  retryAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Cache configuration
const USER_CACHE_KEY = 'cached_user_info';
const USER_CACHE_TTL = 5 * 60 * 1000; // 5 minutes

interface CachedUser {
  data: User;
  timestamp: number;
}

// Role mapping function to handle all role types
const mapBackendRole = (backendRole: string): 'end_user' | 'content_manager' | 'system_administrator' => {
  switch (backendRole.toLowerCase()) {
    case 'admin':
    case 'system_administrator':
      return 'system_administrator';
    case 'content_manager':
      return 'content_manager';
    case 'end_user':
    default:
      return 'end_user';
  }
};

// Get permissions based on role (temporary until backend provides permissions)
const getPermissionsForRole = (role: string): string[] => {
  switch (role) {
    case 'system_administrator':
      return ['read', 'write', 'admin', 'agent_management', 'workflow_management'];
    case 'content_manager':
      return ['read', 'write', 'manage_content'];
    case 'end_user':
    default:
      return ['read', 'write'];
  }
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check cache for user info
  const getCachedUser = (): User | null => {
    try {
      const cached = localStorage.getItem(USER_CACHE_KEY);
      if (!cached) return null;

      const cachedUser: CachedUser = JSON.parse(cached);
      const now = Date.now();

      // Check if cache is still valid
      if (now - cachedUser.timestamp < USER_CACHE_TTL) {
        return cachedUser.data;
      }

      // Cache expired, remove it
      localStorage.removeItem(USER_CACHE_KEY);
      return null;
    } catch (err) {
      console.error('Failed to read cached user:', err);
      localStorage.removeItem(USER_CACHE_KEY);
      return null;
    }
  };

  // Save user to cache
  const cacheUser = (userData: User) => {
    try {
      const cachedUser: CachedUser = {
        data: userData,
        timestamp: Date.now()
      };
      localStorage.setItem(USER_CACHE_KEY, JSON.stringify(cachedUser));
    } catch (err) {
      console.error('Failed to cache user:', err);
    }
  };

  // Load user from backend API
  const loadUser = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Check cache first
      const cachedUser = getCachedUser();
      if (cachedUser) {
        setUser(cachedUser);
        setIsLoading(false);
        return;
      }

      // Fetch user info from backend
      const userInfo = await apiClient.getUserInfo();

      // Map backend user to frontend User type with proper role mapping
      const mappedRole = mapBackendRole(userInfo.role);
      const mappedUser: User = {
        id: userInfo.uuid,
        username: userInfo.name || userInfo.email.split('@')[0],
        email: userInfo.email,
        role: mappedRole,
        permissions: getPermissionsForRole(mappedRole),
        lastLogin: new Date()
      };

      setUser(mappedUser);
      cacheUser(mappedUser);

      // Store user ID in localStorage for backward compatibility
      localStorage.setItem('user_id', userInfo.uuid);
    } catch (err: any) {
      console.error('Failed to load user:', err);

      // Set user-friendly error message
      let errorMessage = 'Unable to authenticate. ';
      if (err.response?.status === 401) {
        errorMessage += 'Your session has expired. Please log in again.';
      } else if (err.response?.status === 403) {
        errorMessage += 'You do not have permission to access this application.';
      } else if (err.response?.status >= 500) {
        errorMessage += 'The server is currently unavailable. Please try again later.';
      } else if (err.message?.includes('Network Error')) {
        errorMessage += 'Cannot connect to the server. Please check your internet connection.';
      } else {
        errorMessage += 'Please try again or contact support if the problem persists.';
      }

      setError(errorMessage);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
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
    setError(null);
    localStorage.removeItem('user');
    localStorage.removeItem(USER_CACHE_KEY);
    localStorage.removeItem('user_id');
  };

  const updateUser = (userData: Partial<User>) => {
    if (user) {
      const updatedUser = { ...user, ...userData };
      setUser(updatedUser);
      cacheUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));
    }
  };

  const retryAuth = async () => {
    await loadUser();
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    error,
    login,
    logout,
    updateUser,
    retryAuth
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
