import axios from 'axios';
import config, { API_ROUTES }  from '../config/config';
import { getUserData } from '../services/authService';

const api = axios.create({
  baseURL: config.apiUrl,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add an interceptor to include the X-User-UUID header in all requests
api.interceptors.request.use(async function (config) {
  try {
    const userData = await getUserData();
    if (userData && userData.uuid) {
      config.headers['X-User-UUID'] = userData.uuid;
    }
  } catch (error) {
    console.error('Error getting user data:', error);
  }
  return config;
}, function (error) {
  return Promise.reject(error);
});

export const createCollectionWithDocuments = async (formData, onUploadProgress) => {
  try {
    console.log(">>> in API.js");
    console.log("formData: ", formData);
    if (!API_ROUTES.CREATE_COLLECTION) {
      throw new Error('CREATE_COLLECTION route is undefined');
    }
    console.log("Sending request to:", API_ROUTES.CREATE_COLLECTION);
    const response = await api.post(
      API_ROUTES.CREATE_COLLECTION,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress,
      }
    );
    console.log("Response: ", response);
    return response.data;
  } catch (error) {
    console.error('Error creating collection with documents:', error);
    console.error('Error details:', error.response?.data);
    throw error;
  }
};

export const getUserCollections = async () => {
  try {
    const userData = await getUserData();
    if (!userData || !userData.uuid) {
      throw new Error('User UUID not available');
    }
    
    console.log("API_ROUTES.GET_USER_COLLECTIONS:", API_ROUTES.GET_USER_COLLECTIONS);
    console.log("User UUID:", userData.uuid);
    const fullUrl = `${API_ROUTES.GET_USER_COLLECTIONS}${userData.uuid}`;
    console.log("Full URL:", fullUrl);

    const response = await api.get(fullUrl);
    console.log("User collections response:", response);
    return response.data;
  } catch (error) {
    console.error('Error fetching user collections:', error);
    console.error('Error details:', error.response?.data);
    return [];
  }
};

export const getCollectionById = async (collectionId) => {
  try {
    const response = await api.get(`${API_ROUTES.GET_COLLECTION_BY_ID}${collectionId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching collection ${collectionId}:`, error);
    throw error;
  }
};

export const updateCollection = async (collectionId, updateData) => {
  try {
    const response = await api.put(`${API_ROUTES.UPDATE_COLLECTION}${collectionId}`, updateData);
    return response.data;
  } catch (error) {
    console.error(`Error updating collection ${collectionId}:`, error);
    throw error;
  }
};

export const deleteCollection = async (collectionId) => {
  try {
    await api.delete(`${API_ROUTES.DELETE_COLLECTION}${collectionId}`);
  } catch (error) {
    console.error(`Error deleting collection ${collectionId}:`, error);
    throw error;
  }
};

export const addDocumentsToCollection = async (collectionId, formData, onUploadProgress) => {
  try {
    const response = await api.post(`${API_ROUTES.ADD_DOCUMENTS}${collectionId}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    });
    return response.data;
  } catch (error) {
    console.error(`Error adding documents to collection ${collectionId}:`, error);
    throw error;
  }
};

export const removeDocumentFromCollection = async (collectionId, documentId) => {
  try {
    await api.delete(`${API_ROUTES.REMOVE_DOCUMENT}${collectionId}/documents/${documentId}`);
  } catch (error) {
    console.error(`Error removing document ${documentId} from collection ${collectionId}:`, error);
    throw error;
  }
};

export const queryCollection = async (collectionId, query) => {
  try {
    const response = await api.post(`${API_ROUTES.QUERY_COLLECTION}${collectionId}/query`, { query });
    return response.data;
  } catch (error) {
    console.error(`Error querying collection ${collectionId}:`, error);
    throw error;
  }
};

export default {
  createCollectionWithDocuments,
  getUserCollections,
  getCollectionById,
  updateCollection,
  deleteCollection,
  addDocumentsToCollection,
  removeDocumentFromCollection,
  queryCollection,
};