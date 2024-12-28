import React, { createContext, useState, useEffect, useContext } from "react";
import {
  getUserData,
  signIn as signInService,
  signOut as signOutService,
  handleAuthCallback,
  checkAuth,
} from "../services/authService";
import config, { API_ROUTES } from "../config/config";

const AuthContext = createContext({
  user: null,
  loading: true,
  signIn: () => {},
  signOut: () => {},
  fetchUser: () => {},
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = async () => {
    setLoading(true);
    try {
      const userData = await getUserData();
      if (userData && userData.success) {
        setUser(userData.data);
      } else {
        setUser(null);
      }
      setLoading(false);
    } catch (error) {
      console.error("Error fetching user:", error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  // useEffect(() => {
  //   const initAuth = async () => {
  //     // setLoading(true);
  //     try {
  //       const authResult = await handleAuthCallback();
  //       if (authResult.success) {
  //         await fetchUser();
  //       } else {
  //         const { authenticated } = await checkAuth();
  //         if (authenticated) {
  //           await fetchUser();
  //         } else {
  //           setUser(null);
  //         }
  //       }
  //     } catch (error) {
  //       console.error("Error during authentication initialization:", error);
  //       setUser(null);
  //     } finally {
  //       // setLoading(false);
  //     }
  //   };

  //   initAuth();
  // }, []);

  const signIn = () => {
    if (API_ROUTES && API_ROUTES.LOGIN) {
      return signInService();
    } else {
      console.error("LOGIN route is not defined in API_ROUTES");
      return null;
    }
  };

  const signOut = async () => {
    try {
      await signOutService();
      setUser(null);
    } catch (error) {
      console.error("Error logging out:", error);
    }
  };

  const value = {
    user,
    loading,
    signIn,
    signOut,
    fetchUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export default AuthContext;
