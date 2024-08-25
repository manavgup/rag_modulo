import { UserManager, WebStorageStateStore } from 'oidc-client';
import config from '../config/config';

const getOidcConfig = async () => {
  try {
    console.log('Fetching OIDC config from:', `${config.apiUrl}/auth/oidc-config`);
    const response = await fetch(`${config.apiUrl}/auth/oidc-config`);
    console.log('OIDC config response status:', response.status);
    const oidcConfig = await response.json();
    console.log('OIDC Config Response:', oidcConfig);
    return oidcConfig;
  } catch (error) {
    console.error('Error fetching OIDC config:', error);
    throw error;
  }
};

let userManager = null;

const createUserManager = async () => {
  if (userManager) return userManager;

  const oidcConfig = await getOidcConfig();
  userManager = new UserManager({
    ...oidcConfig,
    userStore: new WebStorageStateStore({ store: window.localStorage }),
    metadata: {
      ...oidcConfig.metadata,
      token_endpoint: `${config.apiUrl}/auth/token`,
      userinfo_endpoint: `${config.apiUrl}/auth/userinfo`,
    },
  });
  return userManager;
};

export const signIn = async () => {
  const userManager = await createUserManager();
  return userManager.signinRedirect();
};

export const getUser = async () => {
  const userManager = await createUserManager();
  return userManager.getUser();
};

export const handleCallback = async () => {
  const userManager = await createUserManager();
  return userManager.signinRedirectCallback();
};

export const signOut = async () => {
  const userManager = await createUserManager();
  return userManager.signoutRedirect();
};