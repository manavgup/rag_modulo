import { api, handleApiError } from "./axios";
import { API_ROUTES } from "../config/config";

const createAssistant = async (formData, onUploadProgress) => {
  try {
    const url = API_ROUTES.CREATE_ASSISTANT;
    const response = await api.post(url, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress,
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error, "Error creating assistant");
  }
};

const getAssistants = async () => {
  try {
    const url = `${API_ROUTES.GET_ASSISTANTS}/`;
    const response = await api.get(url);

    console.log(url)
    console.log (api.defaults.baseURL);

    return response.data;
  } catch (error) {
    console.error("Error in getUserAssistants:", error);
    throw handleApiError(error, "Error fetching assistants");
  }
};

const updateAssistant = async (assistantId, data) => {
  try {
    const url = `${API_ROUTES.UPDATE_ASSISTANT}${assistantId}`;
    const response = await api.put(url, data);
    return response.data;
  } catch (error) {
    console.error("Error in updateAssistant:", error);
    throw handleApiError(error, "Error updating assistant");
  }
};

const deleteAssistant = async (assistantId) => {
  try {
    const url = `${API_ROUTES.DELETE_ASSISTANT}${assistantId}`;
    const response = await api.delete(url);
    return response.data;
  } catch (error) {
    console.error("Error in deleteAssistant:", error);
    throw handleApiError(error, "Error deleting assistant");
  }
};

export {
  getAssistants,
  createAssistant,
  updateAssistant,
  deleteAssistant,
};
