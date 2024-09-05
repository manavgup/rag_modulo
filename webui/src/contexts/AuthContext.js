import React, { createContext, useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { getUserData } from '../services/authService';

axios.defaults.withCredentials = true;

const AuthContext = createContext({
  user: null,
  loading: true,
  logout: () => {}
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchUser() {
      try {
        console.log("Fetching user data...");
        const userData = await getUserData();
        console.log("User data received:", userData);
        setUser(userData);
      } catch (error) {
        console.error('Error fetching user:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchUser();
  }, []);

  const logout = async () => {
    try {
      await axios.get('/api/auth/logout');
      setUser(null);
      localStorage.removeItem('user_id');
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  const value = {
    user,
    loading,
    logout
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;