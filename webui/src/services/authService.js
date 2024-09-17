import config from '../config/config';

export const signIn = () => {
  window.location.href = `${config.apiUrl}/auth/login`;
};

export const getUserData = async () => {
  try {
    console.log("Fetching user data...");
    const response = await fetch(`${config.apiUrl}/auth/session`, {
      credentials: 'include' // This is important for including cookies
    });
    console.log("Session response:", response);
    if (response.ok) {
      const data = await response.json();
      console.log("User data from server:", data);
      return data.user;
    } else if (response.status === 401) {
      console.log("User not authenticated. Redirecting to login.");
      signIn();
      return null;
    }
    return null;
  } catch (error) {
    console.error("Error fetching user data:", error);
    return null;
  }
};

export const signOut = async () => {
  try {
    await fetch(`${config.apiUrl}/auth/logout`, {
      method: 'GET',
      credentials: 'include'
    });
    // Clear any local storage or state related to authentication
    // For example, if you're storing the user info in localStorage:
    localStorage.removeItem('user');
    window.location.href = '/'; // Redirect to home page after logout
  } catch (error) {
    console.error("Error during sign out:", error);
  }
};

export const logout = signOut;

export const handleAuthCallback = () => {
  const urlParams = new URLSearchParams(window.location.search);
  const error = urlParams.get('error');
  if (error) {
    console.error("Authentication error:", error);
    return false;
  }
  // The actual token exchange happens on the server side in the callback route
  // Here, we just need to check if the authentication was successful
  const userId = urlParams.get('user_id');
  if (userId) {
    // Authentication successful, you might want to fetch user data here
    getUserData();
    // Remove the query parameters from the URL
    window.history.replaceState({}, document.title, window.location.pathname);
    return true;
  }
  return false;
};