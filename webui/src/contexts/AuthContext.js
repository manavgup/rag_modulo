import React, { createContext, useState, useEffect, useContext } from 'react';
import { getUserData, signIn as signInService, signOut as signOutService, handleAuthCallback, checkAuth } from '../services/authService';
import config, { API_ROUTES } from '../config/config';

console.log('AuthContext initialized with config:', config);

const AuthContext = createContext({
  user: null,
  loading: true,
  signIn: () => {},
  signOut: () => {},
  fetchUser: () => {}
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = async () => {
    try {
      console.log("Fetching user data...");
      const userData = await getUserData();
      console.log("User data received:", userData);
      if (userData && userData.success) {
        setUser(userData.data);
      } else {
        console.warn("No user data received");
        setUser(null);
      }
    } catch (error) {
      console.error('Error fetching user:', error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      setLoading(true);
      try {
        console.log("Initializing authentication...");
        const authResult = handleAuthCallback();
        console.log("Auth callback result:", authResult);
        if (authResult.success) {
          console.log("Auth callback handled successfully, fetching user data...");
          await fetchUser();
        } else {
          console.log("Checking authentication status...");
          const { authenticated } = await checkAuth();
          if (authenticated) {
            console.log("User is authenticated, fetching user data...");
            await fetchUser();
          } else {
            console.log("User is not authenticated");
            setUser(null);
          }
        }
      } catch (error) {
        console.error("Error during authentication initialization:", error);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const signIn = () => {
    console.log("Initiating sign-in process...");
    console.log("Config:", config);
    console.log("API_ROUTES:", API_ROUTES);
    if (API_ROUTES && API_ROUTES.LOGIN) {
      console.log("Sign-in URL:", `${config.apiUrl}${API_ROUTES.LOGIN}`);
      return signInService();
    } else {
      console.error("LOGIN route is not defined in API_ROUTES");
      return null;
    }
  };

  const signOut = async () => {
    try {
      console.log("Initiating sign-out process...");
      console.log("Sign-out URL:", `${config.apiUrl}${API_ROUTES.LOGOUT}`);
      await signOutService();
      setUser(null);
      console.log("Sign-out successful");
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  const value = {
    user,
    loading,
    signIn,
    signOut,
    fetchUser
  };

  console.log("AuthContext value:", value);

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