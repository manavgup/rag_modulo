// src/config/config.js
const config = {
    apiUrl: process.env.REACT_APP_API_URL || '/api',
    oidcClientId: process.env.REACT_APP_OIDC_CLIENT_ID,
};

console.log("Config:", config);

const API_ROUTES = {
    CREATE_COLLECTION: `/collections/create__with_documents`,
    GET_USER_COLLECTIONS: `/user-collections/`,
    GET_COLLECTION_BY_ID: `/collections/`,
    UPDATE_COLLECTION: `/collections/`,
    DELETE_COLLECTION: `/collections/`,
    ADD_DOCUMENTS: `/collections/`,
    REMOVE_DOCUMENT: `/collections/`,
    QUERY_COLLECTION: `/collections/`,
    OIDC_CONFIG: `/auth/oidc-config`,
    LOGIN: `/auth/login`,
    LOGOUT: `/auth/logout`,
    SESSION: `/auth/session`,
    CALLBACK: `/auth/callback`,
};

console.log("API_ROUTES:", API_ROUTES);

const authConfig = {
    client_id: config.oidcClientId,
    redirect_uri: `${config.apiUrl}${API_ROUTES.CALLBACK}`,
    response_type: "code",
    scope: "openid profile email",
    post_logout_redirect_uri: config.apiUrl,
};

console.log("authConfig:", authConfig);

export { config as default, API_ROUTES, authConfig };