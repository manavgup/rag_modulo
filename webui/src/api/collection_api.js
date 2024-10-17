import { api, handleApiError } from "./axios";
import { API_ROUTES } from "../config/config";
import { getStoredUserData } from '../services/authService';


const createCollectionWithDocuments = async (formData, onUploadProgress) => {
  try {
    const url = API_ROUTES.CREATE_COLLECTION;
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

const getUserCollections = async () => {
  try {
    const userData = getStoredUserData();
    if (!userData || !userData.uuid) {
      throw new Error('User UUID not available');
    }

    const url = `${API_ROUTES.GET_USER_COLLECTIONS}/${userData.uuid}`;
    const response = await api.get(url);
    return response.data;
    
  } catch (error) {
    console.error('Error in getUserCollections:', error);
    throw handleApiError(error, 'Error fetching user collections');
  }
};

const updateCollection = async (collectionId, data) => {
  try {
    const url = `${API_ROUTES.UPDATE_COLLECTION}${collectionId}`;
    const response = await api.put(url, data);
    return response.data;
  } catch (error) {
    console.error('Error in updateCollection:', error);
    throw handleApiError(error, 'Error updating collection');
  }
};

const deleteCollection = async (collectionId) => {
  try {
    const url = `${API_ROUTES.DELETE_COLLECTION}${collectionId}`;
    const response = await api.delete(url);
    return response.data;
  } catch (error) {
    console.error('Error in deleteCollection:', error);
    throw handleApiError(error, 'Error deleting collection');
  }
};

const getDocumentsInCollection = async (collectionId, currentPage, pageSize, searchTerm, sortField, sortDirection) => {
  try {
    const url = `${API_ROUTES.GET_COLLECTION_BY_ID}${collectionId}/documents?page=${currentPage}&pageSize=${pageSize}&searchTerm=${searchTerm}&sortField=${sortField}&sortDirection=${sortDirection}`;
    const response = await api.get(url);
    return response.data;
  } catch (error) {
    console.error('Error in getDocumentsInCollection:', error);
    throw handleApiError(error, 'Error fetching documents');
  }
};

const deleteDocument = async (collectionId, documentId) => {
  try {
    const url = `${API_ROUTES.DELETE_COLLECTION}${collectionId}/documents/${documentId}`;
    const response = await api.delete(url);
    return response.data;
  } catch (error) {
    console.error('Error in deleteDocument:', error);
    throw handleApiError(error, 'Error deleting document');
  }
};

const moveDocument = async (sourceCollectionId, documentId, targetCollectionId) => {
  try {
    const url = `${API_ROUTES.GET_COLLECTION_BY_ID}${sourceCollectionId}/documents/${documentId}/move`;
    const response = await api.post(url, { targetCollectionId });
    return response.data;
  } catch (error) {
    console.error('Error in moveDocument:', error);
    throw handleApiError(error, 'Error moving document');
  }
};

const getDocument = async (documentId) => {
  try {
    const url = `${API_ROUTES.GET_COLLECTION_BY_ID}documents/${documentId}`;
    const response = await api.get(url);
    return response.data;
  } catch (error) {
    console.error('Error in getDocument:', error);
    throw handleApiError(error, 'Error fetching document');
  }
};

export {
  createCollectionWithDocuments,
  getUserCollections,
  updateCollection,
  deleteCollection,
  getDocumentsInCollection,
  deleteDocument,
  moveDocument,
  getDocument
};