const config = {
    apiUrl: '/api'
};

console.log("Config initialized:", config);
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
    SEARCH: '/search',
    SEARCH_STREAM: '/search/stream'
};

console.log("API_ROUTES:", API_ROUTES);

// Define the function
const getFullApiUrl = (route) => {
    return `${config.apiUrl}${route}`;
};

const authConfig = {
    redirect_uri: `${window.location.origin}/api/auth/callback`,
    response_type: "code",
    scope: "openid profile email",
    post_logout_redirect_uri: window.location.origin,
};

console.log("authConfig:", authConfig);

// Export it in a consolidated manner
export default config;
export { API_ROUTES, authConfig, getFullApiUrl };
