import axios from 'axios';
import API_ROUTES from '../config/config';

const api = axios.create({
  baseURL: API_ROUTES.GET_USER_COLLECTIONS,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const createCollectionWithDocuments = async (formData, onUploadProgress) => {
  try {
    console.log(">>> in API.js");
    console.log("formData: ", formData);
    console.log("Sending request to:", API_ROUTES.CREATE_COLLECTION);
    const response = await axios.post(
      API_ROUTES.CREATE_COLLECTION,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress,
        withCredentials: false,
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

export const getUserCollections = async (userId) => {
  try {
    console.log("API_ROUTES.GET_USER_COLLECTIONS:", API_ROUTES.GET_USER_COLLECTIONS);
    console.log("userId:", userId);
    console.log("Full URL:", `${API_ROUTES.GET_USER_COLLECTIONS}${userId}`);

    const response = await axios.get(`${API_ROUTES.GET_USER_COLLECTIONS}${userId}`, {
      withCredentials: false,
    });
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