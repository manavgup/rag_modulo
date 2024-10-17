import axios from 'axios';
import config, { getFullApiUrl } from '../config/config';

console.log('API configuration:', config);

const api = axios.create({
  baseURL: getFullApiUrl(''),
  headers: {
    'Content-Type': 'application/json',
  },
});

console.log('Axios instance created with baseURL:', api.defaults.baseURL);

// Add an interceptor to include the JWT in the Authorization header for all requests
api.interceptors.request.use(async function (config) {
  console.log('Request interceptor - URL:', config.url, 'Method:', config.method);
  const token = localStorage.getItem('jwt_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
    console.log('Axios interceptor: Adding token to request headers', config.url);
  } else {
    console.log('Axios interceptor: No token found in localStorage');
  }
  console.log('Final request config:', config);
  return config;
}, function (error) {
  console.error('Axios interceptor: Error in request interceptor', error);
  return Promise.reject(error);
});

// Add an interceptor to handle token expiration
api.interceptors.response.use(
  (response) => {
    console.log('Response interceptor - URL:', response.config.url, 'Status:', response.status);
    return response;
  },
  async (error) => {
    console.error('Response interceptor - Error:', error);
    if (error.response && error.response.status === 401) {
      console.error('Axios interceptor: Unauthorized access, redirecting to login');
      localStorage.removeItem('jwt_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

const handleApiError = (error, customErrorMessage) => {
  console.error('API Error:', error);
  if (error.response) {
    console.error('Response data:', error.response.data);
    console.error('Response status:', error.response.status);
    console.error('Response headers:', error.response.headers);
    return {
      message: customErrorMessage || error.response.data.message || 'An error occurred while processing your request.',
      status: error.response.status
    };
  } else if (error.request) {
    console.error('Request:', error.request);
    return {
      message: 'No response received from the server. Please try again later.',
      status: 0
    };
  } else {
    console.error('Error:', error.message);
    return {
      message: customErrorMessage || error.message || 'An unexpected error occurred. Please try again.',
      status: 0
    };
  }
};

export {
  api,
  handleApiError
};
