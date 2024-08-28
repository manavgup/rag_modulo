import config from '../config/config';

export const signIn = () => {
  window.location.href = `${config.apiUrl}/auth/login`;
};

export const getUserData = async () => {
  try {
    const response = await fetch(`${config.apiUrl}/auth/session`, {
      credentials: 'include'
    });
    if (response.ok) {
      const data = await response.json();
      if (data.user && data.user_id) {
        localStorage.setItem('user_uuid', data.user_id);
        return { ...data.user, id: data.user_id };
      }
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
    localStorage.removeItem('user_uuid');
  } catch (error) {
    console.error("Error during sign out:", error);
  }
};

export const getUserUUID = () => {
  return localStorage.getItem('user_uuid');
};