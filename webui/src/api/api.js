// webui/src/api/api.js
import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const createCollectionWithDocuments = async (collectionName, isPrivate, files) => {
  const formData = new FormData();
  formData.append('collection_name', collectionName);
  formData.append('is_private', isPrivate);
  files.forEach((file) => {
    formData.append('files', file);
  });

  try {
    const response = await axios.post(`${BASE_URL}/api/create_collection_with_documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  } catch (error) {
    console.error(error);
    throw new Error('Failed to create collection with documents');
  }
};
