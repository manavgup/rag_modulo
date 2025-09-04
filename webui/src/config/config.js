const config = {
    apiUrl: '/api'
};



const API_ROUTES = {
    // Core endpoints
    COLLECTIONS_ENDPOINT: '/collections',
    CREATE_COLLECTION_WITH_FILES: `/collections/with-files`,
    USERS_ENDPOINT: '/users',
    
    // Auth endpoints
    OIDC_CONFIG: `/auth/oidc-config`,
    LOGIN: `/auth/login`,
    LOGOUT: `/auth/logout`,
    SESSION: `/auth/session`,
    CALLBACK: `/auth/callback`,
    USERINFO: `/auth/userinfo`,
    
    // Search endpoints
    SEARCH: '/search',
    SEARCH_STREAM: '/search/stream',
    
    // Configuration endpoints
    PROVIDERS: '/users/{userId}/llm-providers',
    PROVIDER_CONFIG: '/users/{userId}/llm-providers',
    PROVIDER_MODELS: '/users/{userId}/llm-providers/{providerId}/models',
    PIPELINES: '/users/{userId}/pipelines',
    LLM_PARAMETERS: '/users/{userId}/llm-parameters',
    PROMPT_TEMPLATES: '/users/{userId}/prompt-templates',
    
    // Provider operations
    PROVIDER_DEFAULT: '/users/{userId}/llm-providers/{providerId}/default',
    PROVIDER_VALIDATE: '/users/{userId}/llm-providers/{providerId}/validate',
    PROVIDER_TEST: '/users/{userId}/llm-providers/{providerId}/test',
    
    // Pipeline operations
    PIPELINE_DEFAULT: '/users/{userId}/pipelines/{pipelineId}/default',
    PIPELINE_VALIDATE: '/users/{userId}/pipelines/{pipelineId}/validate',
    PIPELINE_TEST: '/users/{userId}/pipelines/{pipelineId}/test',
    
    // Parameter operations
    PARAMETERS_DEFAULT: '/users/{userId}/llm-parameters/{parameterId}/default',
    PARAMETERS_VALIDATE: '/users/{userId}/llm-parameters/{parameterId}/validate',
    
    // Template operations
    TEMPLATE_DEFAULT: '/users/{userId}/prompt-templates/{templateId}/default',
    TEMPLATE_VALIDATE: '/users/{userId}/prompt-templates/{templateId}/validate'
};



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



// Export it in a consolidated manner
export default config;
export { API_ROUTES, authConfig, getFullApiUrl };
