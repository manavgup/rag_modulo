import axios from 'axios';
import config from '../config/config';
import { getUserData } from '../services/authService';

const api = axios.create({
  baseURL: config.apiUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add an interceptor to include the JWT in the Authorization header for all requests
api.interceptors.request.use(async function (config) {
  try {
    const userData = await getUserData();
    if (userData && userData.token) {
      config.headers['Authorization'] = `Bearer ${userData.token}`;
    }
  } catch (error) {
    console.error('Error getting user data:', error);
  }
  return config;
}, function (error) {
  return Promise.reject(error);
});

// Add an interceptor to handle token expiration
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const newToken = await refreshToken();
        axios.defaults.headers.common['Authorization'] = 'Bearer ' + newToken;
        return api(originalRequest);
      } catch (refreshError) {
        // If token refresh fails, redirect to login
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
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
    console.error('Error message:', error.message);
    return {
      message: customErrorMessage || 'An unexpected error occurred. Please try again.',
      status: 0
    };
  }
};

/**
 * Create a new collection with documents
 * @param {FormData} formData - The form data containing collection details and files
 * @param {function} onUploadProgress - Callback function for upload progress
 * @returns {Promise<Object>} The created collection data
 */
export const createCollectionWithDocuments = async (formData, onUploadProgress) => {
  try {
    if (!API_ROUTES.CREATE_COLLECTION) {
      throw new Error('CREATE_COLLECTION route is undefined');
    }
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
    return response.data;
  } catch (error) {
    throw handleApiError(error, 'Error creating collection with documents');
  }
};

/**
 * Get user collections
 * @param {number} page - The page number
 * @param {number} pageSize - The number of items per page
 * @param {string} searchTerm - Optional search term
 * @param {string} sortField - Field to sort by
 * @param {string} sortDirection - Sort direction ('asc' or 'desc')
 * @returns {Promise<Object>} The user collections data
 */
export const getUserCollections = async (page = 1, pageSize = 10, searchTerm = '', sortField = 'name', sortDirection = 'asc') => {
  try {
    const userData = await getUserData();
    if (!userData || !userData.uuid) {
      throw new Error('User UUID not available');
    }
    
    const response = await api.get(API_ROUTES.GET_USER_COLLECTIONS, {
      params: {
        uuid: userData.uuid,
        page,
        pageSize,
        searchTerm,
        sortField,
        sortDirection
      }
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error, 'Error fetching user collections');
  }
};

/**
 * Get a collection by its ID
 * @param {string} collectionId - The ID of the collection
 * @returns {Promise<Object>} The collection data
 */
export const getCollectionById = async (collectionId) => {
  try {
    const response = await api.get(`${API_ROUTES.GET_COLLECTION_BY_ID}${collectionId}`);
    return response.data;
  } catch (error) {
    throw handleApiError(error, `Error fetching collection ${collectionId}`);
  }
};

/**
 * Update a collection
 * @param {string} collectionId - The ID of the collection to update
 * @param {Object} updateData - The data to update
 * @returns {Promise<Object>} The updated collection data
 */
export const updateCollection = async (collectionId, updateData) => {
  try {
    const response = await api.put(`${API_ROUTES.UPDATE_COLLECTION}${collectionId}`, updateData);
    return response.data;
  } catch (error) {
    throw handleApiError(error, `Error updating collection ${collectionId}`);
  }
};

/**
 * Delete a collection
 * @param {string} collectionId - The ID of the collection to delete
 * @returns {Promise<void>}
 */
export const deleteCollection = async (collectionId) => {
  try {
    await api.delete(`${API_ROUTES.DELETE_COLLECTION}${collectionId}`);
  } catch (error) {
    throw handleApiError(error, `Error deleting collection ${collectionId}`);
  }
};

/**
 * Delete a document from a collection
 * @param {string} collectionId - The ID of the collection
 * @param {string} documentId - The ID of the document to delete
 * @returns {Promise<void>}
 */
export const deleteDocument = async (collectionId, documentId) => {
  try {
    await api.delete(`${API_ROUTES.REMOVE_DOCUMENT}${collectionId}/documents/${documentId}`);
  } catch (error) {
    throw handleApiError(error, `Error deleting document ${documentId}`);
  }
};

/**
 * Add documents to a collection
 * @param {string} collectionId - The ID of the collection
 * @param {FormData} formData - The form data containing the documents
 * @param {function} onUploadProgress - Callback function for upload progress
 * @returns {Promise<Object>} The updated collection data
 */
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
    throw handleApiError(error, `Error adding documents to collection ${collectionId}`);
  }
};

/**
 * Remove a document from a collection
 * @param {string} collectionId - The ID of the collection
 * @param {string} documentId - The ID of the document to remove
 * @returns {Promise<void>}
 */
export const removeDocumentFromCollection = async (collectionId, documentId) => {
  try {
    await api.delete(`${API_ROUTES.REMOVE_DOCUMENT}${collectionId}/documents/${documentId}`);
  } catch (error) {
    throw handleApiError(error, `Error removing document ${documentId} from collection ${collectionId}`);
  }
};

/**
 * Move a document from one collection to another
 * @param {string} documentId - The ID of the document to move
 * @param {string} sourceCollectionId - The ID of the source collection
 * @param {string} targetCollectionId - The ID of the target collection
 * @returns {Promise<Object>} The moved document data
 */
export const moveDocument = async (documentId, sourceCollectionId, targetCollectionId) => {
  try {
    const response = await api.post(API_ROUTES.MOVE_DOCUMENT, {
      documentId,
      sourceCollectionId,
      targetCollectionId
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error, `Error moving document ${documentId}`);
  }
};

/**
 * Get documents in a collection
 * @param {string} collectionId - The ID of the collection
 * @param {number} page - The page number (optional, default: 1)
 * @param {number} pageSize - The number of items per page (optional, default: 10)
 * @returns {Promise<Object>} The documents data
 */
export const getDocumentsInCollection = async (collectionId, page = 1, pageSize = 10) => {
  try {
    const response = await api.get(`${API_ROUTES.GET_DOCUMENTS_IN_COLLECTION}${collectionId}`, {
      params: { page, pageSize }
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error, `Error fetching documents in collection ${collectionId}`);
  }
};

/**
 * Query a collection
 * @param {string} collectionId - The ID of the collection to query
 * @param {string} query - The query string
 * @returns {Promise<Object>} The query results
 */
export const queryCollection = async (collectionId, query) => {
  try {
    const response = await api.post(`${API_ROUTES.QUERY_COLLECTION}${collectionId}/query`, { query });
    return response.data;
  } catch (error) {
    throw handleApiError(error, `Error querying collection ${collectionId}`);
  }
};

/**
 * Get a document by its ID
 * @param {string} documentId - The ID of the document
 * @returns {Promise<Object>} The document data
 */
export const getDocument = async (documentId) => {
  try {
    const response = await api.get(`${API_ROUTES.GET_DOCUMENT}${documentId}`);
    return response.data;
  } catch (error) {
    throw handleApiError(error, `Error fetching document ${documentId}`);
  }
};

/**
 * Update document metadata
 * @param {string} documentId - The ID of the document
 * @param {Object} metadata - The metadata to update
 * @returns {Promise<Object>} The updated document data
 */
export const updateDocumentMetadata = async (documentId, metadata) => {
  try {
    const response = await api.put(`${API_ROUTES.UPDATE_DOCUMENT_METADATA}${documentId}`, metadata);
    return response.data;
  } catch (error) {
    throw handleApiError(error, `Error updating metadata for document ${documentId}`);
  }
};

/**
 * Get document versions
 * @param {string} documentId - The ID of the document
 * @returns {Promise<Object>} The document versions data
 */
export const getDocumentVersions = async (documentId) => {
  try {
    const response = await api.get(`${API_ROUTES.GET_DOCUMENT_VERSIONS}${documentId}/versions`);
    return response.data;
  } catch (error) {
    throw handleApiError(error, `Error fetching versions for document ${documentId}`);
  }
};

/**
 * Get recent documents
 * @param {number} limit - The number of recent documents to fetch
 * @returns {Promise<Object>} The recent documents data
 */
export const getRecentDocuments = async (limit = 5) => {
  try {
    const response = await api.get(API_ROUTES.GET_RECENT_DOCUMENTS, { params: { limit } });
    return response.data;
  } catch (error) {
    throw handleApiError(error, 'Error fetching recent documents');
  }
};

/**
 * Get usage statistics
 * @returns {Promise<Object>} The usage statistics data
 */
export const getUsageStatistics = async () => {
  try {
    const response = await api.get(API_ROUTES.GET_USAGE_STATISTICS);
    return response.data;
  } catch (error) {
    throw handleApiError(error, 'Error fetching usage statistics');
  }
};

/**
 * Refresh the JWT token
 * @returns {Promise<string>} The new token
 */
export const refreshToken = async () => {
  try {
    const response = await axios.post(`${config.apiUrl}/auth/token`, null, {
      withCredentials: true,
    });
    const { token } = response.data;
    localStorage.setItem('jwt_token', token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    return token;
  } catch (error) {
    console.error('Error refreshing token:', error);
    if (error.response && error.response.status === 401) {
      window.location.href = '/login';
    }
    throw error;
  }
};

export default {
  createCollectionWithDocuments,
  getUserCollections,
  getCollectionById,
  updateCollection,
  deleteCollection,
  deleteDocument,
  addDocumentsToCollection,
  removeDocumentFromCollection,
  queryCollection,
  getDocument,
  updateDocumentMetadata,
  getDocumentVersions,
  getRecentDocuments,
  getUsageStatistics,
  refreshToken,
};
