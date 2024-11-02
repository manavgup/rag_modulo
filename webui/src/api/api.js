import axios from 'axios';
import config, { API_ROUTES, getFullApiUrl } from '../config/config';
import { getStoredUserData } from '../services/authService';

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

export const createCollectionWithDocuments = async (formData, onUploadProgress) => {
  try {
    const url = API_ROUTES.CREATE_COLLECTION_WITH_FILES;
    console.log('Creating collection with documents:', getFullApiUrl(url));
    const response = await api.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error, 'Error creating collection with documents');
  }
};

export const getUserCollections = async () => {
  try {
    const userData = getStoredUserData();
    if (!userData || !userData.uuid) {
      throw new Error('User UUID not available');
    }

    const url = `${API_ROUTES.USERS_ENDPOINT}/${userData.uuid}/collections`;
    console.log('Fetching user collections:', getFullApiUrl(url));
    const response = await api.get(url);
    console.log('User collections fetched successfully', response.data);
    return response.data;
    
  } catch (error) {
    console.error('Error in getUserCollections:', error);
    throw handleApiError(error, 'Error fetching user collections');
  }
};

export const updateCollection = async (collectionId, data) => {
  try {
    const url = `${API_ROUTES.COLLECTIONS_ENDPOINT}/${collectionId}`;
    console.log('Updating collection:', getFullApiUrl(url));
    const response = await api.put(url, data);
    console.log('Collection updated successfully:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error in updateCollection:', error);
    throw handleApiError(error, 'Error updating collection');
  }
};

export const deleteCollection = async (collectionId) => {
  try {
    const url = `${API_ROUTES.COLLECTIONS_ENDPOINT}/${collectionId}`;
    console.log('Deleting collection:', getFullApiUrl(url));
    const response = await api.delete(url);
    console.log('Collection deleted successfully:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error in deleteCollection:', error);
    throw handleApiError(error, 'Error deleting collection');
  }
};

export const getDocumentsInCollection = async (collectionId, currentPage, pageSize, searchTerm, sortField, sortDirection) => {
  try {
    const url = `${API_ROUTES.COLLECTIONS_ENDPOINT}/${collectionId}/documents?page=${currentPage}&pageSize=${pageSize}&searchTerm=${searchTerm}&sortField=${sortField}&sortDirection=${sortDirection}`;
    console.log('Fetching documents in collection:', getFullApiUrl(url));
    const response = await api.get(url);
    console.log('Documents fetched successfully:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error in getDocumentsInCollection:', error);
    throw handleApiError(error, 'Error fetching documents');
  }
};

export const deleteDocument = async (collectionId, documentId) => {
  try {
    const url = `${API_ROUTES.COLLECTIONS_ENDPOINT}/${collectionId}/documents/${documentId}`;
    console.log('Deleting document:', getFullApiUrl(url));
    const response = await api.delete(url);
    console.log('Document deleted successfully:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error in deleteDocument:', error);
    throw handleApiError(error, 'Error deleting document');
  }
};

export const moveDocument = async (sourceCollectionId, documentId, targetCollectionId) => {
  try {
    const url = `${API_ROUTES.COLLECTIONS_ENDPOINT}/${sourceCollectionId}/documents/${documentId}/move`;
    console.log('Moving document:', getFullApiUrl(url));
    const response = await api.post(url, { targetCollectionId });
    console.log('Document moved successfully:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error in moveDocument:', error);
    throw handleApiError(error, 'Error moving document');
  }
};

export const getDocument = async (documentId) => {
  try {
    const url = `${API_ROUTES.COLLECTIONS_ENDPOINT}/documents/${documentId}`;
    console.log('Fetching document:', getFullApiUrl(url));
    const response = await api.get(url);
    console.log('Document fetched successfully:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error in getDocument:', error);
    throw handleApiError(error, 'Error fetching document');
  }
};

export default {
  createCollectionWithDocuments,
  getUserCollections,
  updateCollection,
  deleteCollection,
  getDocumentsInCollection,
  deleteDocument,
  moveDocument,
  getDocument
};