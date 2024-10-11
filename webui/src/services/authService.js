import config, { API_ROUTES, getFullApiUrl } from '../config/config';

export const signIn = () => {
  const loginUrl = getFullApiUrl(API_ROUTES.LOGIN);
  return loginUrl;
};

export const handleAuthCallback = async () => {
  const urlParams = await new URLSearchParams(window.location.search);
  const token = urlParams.get('token');

  if (token) {
    try {
      localStorage.setItem('jwt_token', token);
      // Remove the token from the URL
      window.history.replaceState({}, document.title, window.location.pathname);
      return { success: true };
    } catch (error) {
      console.error("Error storing token:", error);
      return { success: false, error: "Token storage failed" };
    }
  }

  return { success: false, error: "No token received" };
};

export const fetchWithAuthHeader = async (url, options = {}) => {
  const token = localStorage.getItem('jwt_token');
  if (!token) {
    console.error("No token found, unable to proceed.");
    return null;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorDetails = await response.text();
      console.error(`Error response from ${url}:`, response.status, errorDetails);
      throw new Error(`Error ${response.status}: ${errorDetails}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error in fetchWithAuthHeader:", error);
    throw error;
  }
};

export const getUserData = async () => {
  try {
    const userDataUrl = getFullApiUrl(API_ROUTES.USERINFO);
    const userData = await fetchWithAuthHeader(userDataUrl);
    localStorage.setItem('user_data', JSON.stringify(userData));
    return { success: true, data: userData };
  } catch (error) {
    console.error("Error fetching user data:", error);
    return { success: false, error: error.message };
  }
};

export const signOut = async () => {
  try {
    const logoutUrl = getFullApiUrl(API_ROUTES.LOGOUT);
    await fetchWithAuthHeader(logoutUrl, { method: 'POST' });
    return { success: true };
  } catch (error) {
    console.error("Error during sign out:", error);
    return { success: false, error: error.message };
  } finally {
    clearAuthData();
  }
};

const clearAuthData = () => {
  localStorage.removeItem('jwt_token');
  localStorage.removeItem('user_data');
  // Clear any other auth-related data here
};

export const logout = signOut;

export const checkAuth = async () => {
  const token = localStorage.getItem('jwt_token');
  if (!token) {
    return { isAuthenticated: false };
  }

  try {
    const checkAuthUrl = getFullApiUrl(API_ROUTES.SESSION);
    const response = await fetchWithAuthHeader(checkAuthUrl);
    return { isAuthenticated: response && response.authenticated };
  } catch (error) {
    console.error("Error checking authentication:", error);
    return { isAuthenticated: false, error: error.message };
  }
};

export const getStoredUserData = () => {
  const userData = localStorage.getItem('user_data');
  return userData ? JSON.parse(userData) : null;
};

// Global error handler
export const handleError = (error) => {
  console.error("Global error:", error);
  // Implement global error handling logic here
  // For example, show a notification to the user
};