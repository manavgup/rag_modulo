import axios from 'axios';
import API_ROUTES from './config';

export const createCollectionWithDocuments = async (formData, onUploadProgress) => {
  try {
    console.log(">>> in API.js")
    console.log("formData: ", formData)
    const response = await axios.post(
      API_ROUTES.CREATE_COLLECTION,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress,
        withCredentials: false,  // Ensure this is set to false
      }
    );
    console.log("Response: ", response)
    return response.data;
  } catch (error) {
    console.error('Error creating collection with documents:', error);
    throw error;
  }
};
