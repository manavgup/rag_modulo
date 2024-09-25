import config, { API_ROUTES, getFullApiUrl } from '../config/config';

console.log('Auth service initialized with config:', config);

export const signIn = () => {
  console.log("Initiating sign-in process");
  const loginUrl = getFullApiUrl(API_ROUTES.LOGIN);
  console.log("Login URL:", loginUrl);
  return loginUrl;
};

export const handleAuthCallback = () => {
  console.log("Handling auth callback");
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  console.log("Received token:", token ? "Token present" : "No token");

  if (token) {
    try {
      localStorage.setItem('jwt_token', token);
      console.log("Token received and stored");
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
    console.log(`Fetching ${url} with auth header`);
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
    console.log(`Successful response from ${url}:`, data);
    return data;
  } catch (error) {
    console.error("Error in fetchWithAuthHeader:", error);
    throw error;
  }
};

export const getUserData = async () => {
  console.log("Fetching user data...");
  try {
    const userDataUrl = getFullApiUrl(API_ROUTES.USERINFO);
    console.log("User data URL:", userDataUrl);
    const userData = await fetchWithAuthHeader(userDataUrl);
    console.log("User data retrieved:", userData);
    localStorage.setItem('user_data', JSON.stringify(userData));
    return { success: true, data: userData };
  } catch (error) {
    console.error("Error fetching user data:", error);
    return { success: false, error: error.message };
  }
};

export const signOut = async () => {
  console.log("Initiating sign-out process");
  try {
    const logoutUrl = getFullApiUrl(API_ROUTES.LOGOUT);
    console.log("Logout URL:", logoutUrl);
    await fetchWithAuthHeader(logoutUrl, { method: 'POST' });
    console.log("Logout successful");
    return { success: true };
  } catch (error) {
    console.error("Error during sign out:", error);
    return { success: false, error: error.message };
  } finally {
    clearAuthData();
  }
};

const clearAuthData = () => {
  console.log("Clearing auth data");
  localStorage.removeItem('jwt_token');
  localStorage.removeItem('user_data');
  // Clear any other auth-related data here
};

export const logout = signOut;

export const checkAuth = async () => {
  console.log("Checking authentication status");
  const token = localStorage.getItem('jwt_token');
  if (!token) {
    console.log("No token found, user is not authenticated");
    return { isAuthenticated: false };
  }

  try {
    const checkAuthUrl = getFullApiUrl(API_ROUTES.SESSION);
    console.log("Check auth URL:", checkAuthUrl);
    const response = await fetchWithAuthHeader(checkAuthUrl);
    console.log("Authentication check result:", response);
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