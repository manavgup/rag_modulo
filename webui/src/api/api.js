import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const createCollectionWithDocuments = async (formData, onUploadProgress) => {
  try {
    console.log(">>> in API.js")
    console.log("formData: ", formData)
    const response = await axios.post(
      `${BASE_URL}/api/create_collection_with_documents`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress,
      }
    );
    console.log("Response: ", response)
    return response.data;
  } catch (error) {
    console.error('Error creating collection with documents:', error);
    throw error;
  }
};
