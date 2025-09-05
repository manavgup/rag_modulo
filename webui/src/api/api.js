import axios from 'axios';
import config, { API_ROUTES, getFullApiUrl } from '../config/config';
import { getStoredUserData } from '../services/authService';



const api = axios.create({
  baseURL: getFullApiUrl(''),
  headers: {
    'Content-Type': 'application/json',
  },
});



// Add an interceptor to include the JWT in the Authorization header for all requests
api.interceptors.request.use(async function (config) {
  const token = localStorage.getItem('jwt_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
}, function (error) {
  console.error('Axios interceptor: Error in request interceptor', error);
  return Promise.reject(error);
});

// Add an interceptor to handle token expiration
api.interceptors.response.use(
  (response) => {
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

export const searchDocuments = async (query, collectionId) => {
  try {
    const url = API_ROUTES.SEARCH;


    if (collectionId === 'all') {
      throw new Error('Please select a specific collection to search');
    }

    // First, fetch the default pipeline for the collection
    const userData = getStoredUserData();
    if (!userData || !userData.uuid) {
      throw new Error('User UUID not available');
    }

    const pipelinesUrl = `${API_ROUTES.USERS_ENDPOINT}/${userData.uuid}/pipelines?collection_id=${collectionId}&is_default=true`;
    const pipelinesResponse = await api.get(pipelinesUrl);

    if (!pipelinesResponse.data || pipelinesResponse.data.length === 0) {
      throw new Error('No default pipeline found for the selected collection');
    }

    const defaultPipelineId = pipelinesResponse.data[0].id;

    const response = await api.post(url, {
      question: query,
      collection_id: collectionId,
      pipeline_id: defaultPipelineId,
      user_id: userData.uuid
    });



    return {
      answer: response.data.answer,
      query_results: response.data.query_results || [],
      documents: response.data.documents || [],
      rewritten_query: response.data.rewritten_query,
      evaluation: response.data.evaluation
    };
  } catch (error) {
    console.error('Error in searchDocuments:', error);

    // Log more details about the error
    if (error.response) {
      console.error('Error response details:', error.response.data);
      console.error('Error status:', error.response.status);
    }

    throw handleApiError(error, 'Error searching documents');
  }
};

export const searchDocumentsStream = async (query, collectionId) => {
  try {
    const url = API_ROUTES.SEARCH_STREAM;


    // Skip if 'all' is selected
    if (collectionId === 'all') {
      throw new Error('Please select a specific collection to search');
    }

    const response = await api.post(url, {
      question: query,  // Changed from query to question to match backend schema
      collection_id: collectionId  // Backend will validate UUID format
    }, {
      responseType: 'stream'
    });
    return response.data;
  } catch (error) {
    console.error('Error in searchDocumentsStream:', error);
    throw handleApiError(error, 'Error streaming search results');
  }
};

export const createCollectionWithDocuments = async (formData, onUploadProgress) => {
  try {
    const url = API_ROUTES.CREATE_COLLECTION_WITH_FILES;


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

    const response = await api.get(url);

    // Transform the data structure
    const collections = Array.isArray(response.data) ? response.data : (response.data.collections || []);
    return {
      collections: collections.map(collection => ({
        id: collection.collection_id || collection.id,
        ...collection,
      }))
    };
  } catch (error) {
    console.error('Error in getUserCollections:', error);
    throw handleApiError(error, 'Error fetching user collections');
  }
};

export const updateCollection = async (collectionId, data) => {
  try {
    const url = `${API_ROUTES.COLLECTIONS_ENDPOINT}/${collectionId}`;
    const response = await api.put(url, data);
    return response.data;
  } catch (error) {
    console.error('Error in updateCollection:', error);
    throw handleApiError(error, 'Error updating collection');
  }
};

export const deleteCollection = async (collectionId) => {
  try {
    const url = `${API_ROUTES.COLLECTIONS_ENDPOINT}/${collectionId}`;
    const response = await api.delete(url);
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
  getDocument,
  searchDocuments,
  searchDocumentsStream
};
