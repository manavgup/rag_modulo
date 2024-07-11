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
    return response.data; // Return the success response
  } catch (error) {
    // Handle errors more gracefully
    if (error.response) {
      // The request was made and the server responded with a status code
      console.error('Server responded with an error:', error.response.data);
      throw error.response; // Propagate the error response to the component for handling
    } else if (error.request) {
      // The request was made but no response was received
      console.error('No response received:', error.request);
      throw new Error('No response received from server');
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Error:', error.message);
      throw new Error('An error occurred while sending the request');
    }
  }
};

// ... other API functions can be added here
