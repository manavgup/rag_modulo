// src/config/config.js
const config = {
    apiUrl: process.env.REACT_APP_API_URL || '/api',
    oidcClientId: process.env.REACT_APP_OIDC_CLIENT_ID,
  };

console.log("Config:", config);

const API_ROUTES = {
  CREATE_COLLECTION: `${config.apiUrl}/collections/create__with_documents`,
  GET_USER_COLLECTIONS: `${config.apiUrl}/user-collections/`,
  GET_COLLECTION_BY_ID: `${config.apiUrl}/collections/`,
  UPDATE_COLLECTION: `${config.apiUrl}/collections/`,
  DELETE_COLLECTION: `${config.apiUrl}/collections/`,
  ADD_DOCUMENTS: `${config.apiUrl}/collections/`,
  REMOVE_DOCUMENT: `${config.apiUrl}/collections/`,
  QUERY_COLLECTION: `${config.apiUrl}/collections/`,
  OIDC_CONFIG: `${config.apiUrl}/auth/oidc-config`,
};

console.log("API_ROUTES:", API_ROUTES);

const authConfig = {
  client_id: config.oidcClientId,
  redirect_uri: `${window.location.origin}/api/auth/callback`,
  response_type: "code",
  scope: "openid profile email",
  post_logout_redirect_uri: window.location.origin,
};

console.log("authConfig:", authConfig);

export { config as default, API_ROUTES, authConfig };