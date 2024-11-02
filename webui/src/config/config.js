const config = {
    apiUrl: process.env.REACT_APP_API_URL || '/api',
    oidcClientId: process.env.REACT_APP_OIDC_CLIENT_ID,
};

console.log("Config initialized:", config);
console.log("REACT_APP_API_URL:", process.env.REACT_APP_API_URL);
console.log("Window location origin:", window.location.origin);
console.log("Final apiUrl:", config.apiUrl);

const API_ROUTES = {
    COLLECTIONS_ENDPOINT: '/collections',
    CREATE_COLLECTION_WITH_FILES: `/collections/with-files`,
    USERS_ENDPOINT: '/users',
    OIDC_CONFIG: `/auth/oidc-config`,
    LOGIN: `/auth/login`,
    LOGOUT: `/auth/logout`,
    SESSION: `/auth/session`,
    CALLBACK: `/auth/callback`,
    USERINFO: `/auth/userinfo`,
};

console.log("API_ROUTES:", API_ROUTES);

// Define the function
const getFullApiUrl = (route) => {
    return `${window.location.origin}${config.apiUrl}${route}`;
};

const authConfig = {
    client_id: config.oidcClientId,
    // redirect_uri: getFullApiUrl(API_ROUTES.CALLBACK),
    redirect_uri: window.location.origin + '/callback',
    response_type: "code",
    scope: "openid profile email",
    post_logout_redirect_uri: getFullApiUrl(''),
};

console.log("authConfig:", authConfig);

// Export it in a consolidated manner
export default config;
export { API_ROUTES, authConfig, getFullApiUrl };
