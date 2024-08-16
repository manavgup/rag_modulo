const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const API_ROUTES = {
  CREATE_COLLECTION: `${API_BASE_URL}/collections/create__with_documents`,
  // Add other routes here
};

export default API_ROUTES;