import { signIn, handleAuthCallback, getUserData, signOut, checkAuth, fetchWithAuthHeader } from '../authService';
import { API_ROUTES, getFullApiUrl } from '../../config/config';
import jwtDecode from 'jwt-decode';

jest.mock('../../config/config', () => ({
  API_ROUTES: {
    LOGIN: '/auth/login',
    USERINFO: '/auth/userinfo',
    LOGOUT: '/auth/logout',
    SESSION: '/auth/session',
  },
  getFullApiUrl: jest.fn(route => `http://example.com${route}`),
}));

jest.mock('jwt-decode');

const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

global.fetch = jest.fn();

describe('authService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('signIn', () => {
    it('should redirect to the login URL', () => {
      const mockAssign = jest.fn();
      Object.defineProperty(window, 'location', { value: { assign: mockAssign }, writable: true });

      signIn();

      expect(getFullApiUrl).toHaveBeenCalledWith('/auth/login');
      expect(mockAssign).toHaveBeenCalledWith('http://example.com/auth/login');
    });
  });

  describe('handleAuthCallback', () => {
    it('should handle a valid token', () => {
      const mockToken = 'valid.token.here';
      const mockDecodedToken = { exp: Date.now() / 1000 + 3600 };
      jwtDecode.mockReturnValue(mockDecodedToken);

      Object.defineProperty(window, 'location', {
        value: { search: `?token=${mockToken}`, pathname: '/callback' },
        writable: true,
      });

      const result = handleAuthCallback();

      expect(result).toEqual({ success: true });
      expect(localStorage.setItem).toHaveBeenCalledWith('jwt_token', mockToken);
    });

    it('should handle an invalid token', () => {
      const mockToken = 'invalid.token.here';
      const mockDecodedToken = { exp: Date.now() / 1000 - 3600 };
      jwtDecode.mockReturnValue(mockDecodedToken);

      Object.defineProperty(window, 'location', {
        value: { search: `?token=${mockToken}`, pathname: '/callback' },
        writable: true,
      });

      const result = handleAuthCallback();

      expect(result).toEqual({ success: false, error: 'Invalid token' });
      expect(localStorage.setItem).not.toHaveBeenCalled();
    });
  });

  describe('getUserData', () => {
    it('should fetch user data successfully', async () => {
      const mockUserData = { id: '123', name: 'John Doe' };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue(mockUserData),
      });

      localStorage.getItem.mockReturnValue('valid.token.here');
      jwtDecode.mockReturnValue({ exp: Date.now() / 1000 + 3600 });

      const result = await getUserData();

      expect(result).toEqual({ success: true, data: mockUserData });
      expect(fetch).toHaveBeenCalledWith('http://example.com/auth/userinfo', expect.any(Object));
    });

    it('should handle error when fetching user data', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      localStorage.getItem.mockReturnValue('valid.token.here');
      jwtDecode.mockReturnValue({ exp: Date.now() / 1000 + 3600 });

      const result = await getUserData();

      expect(result).toEqual({ success: false, error: 'Network error' });
    });
  });

  describe('signOut', () => {
    it('should sign out successfully', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({}),
      });

      localStorage.getItem.mockReturnValue('valid.token.here');
      jwtDecode.mockReturnValue({ exp: Date.now() / 1000 + 3600 });

      const result = await signOut();

      expect(result).toEqual({ success: true });
      expect(localStorage.removeItem).toHaveBeenCalledWith('jwt_token');
      expect(fetch).toHaveBeenCalledWith('http://example.com/auth/logout', expect.any(Object));
    });

    it('should handle error during sign out', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      localStorage.getItem.mockReturnValue('valid.token.here');
      jwtDecode.mockReturnValue({ exp: Date.now() / 1000 + 3600 });

      const result = await signOut();

      expect(result).toEqual({ success: false, error: 'Network error' });
      expect(localStorage.removeItem).toHaveBeenCalledWith('jwt_token');
    });
  });

  describe('checkAuth', () => {
    it('should return authenticated when valid token exists', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({ authenticated: true }),
      });

      localStorage.getItem.mockReturnValue('valid.token.here');
      jwtDecode.mockReturnValue({ exp: Date.now() / 1000 + 3600 });

      const result = await checkAuth();

      expect(result).toEqual({ isAuthenticated: true });
      expect(fetch).toHaveBeenCalledWith('http://example.com/auth/session', expect.any(Object));
    });

    it('should return not authenticated when no token exists', async () => {
      localStorage.getItem.mockReturnValue(null);

      const result = await checkAuth();

      expect(result).toEqual({ isAuthenticated: false });
      expect(fetch).not.toHaveBeenCalled();
    });
  });

  describe('fetchWithAuthHeader', () => {
    it('should make authenticated request successfully', async () => {
      const mockResponse = { data: 'test' };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue(mockResponse),
        headers: new Headers(),
      });

      localStorage.getItem.mockReturnValue('valid.token.here');
      jwtDecode.mockReturnValue({ exp: Date.now() / 1000 + 3600 });

      const result = await fetchWithAuthHeader('http://example.com/api/data');

      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith('http://example.com/api/data', expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': 'Bearer valid.token.here'
        })
      }));
    });

    it('should handle 401 error and redirect to login', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: jest.fn().mockResolvedValue('Unauthorized'),
      });

      localStorage.getItem.mockReturnValue('invalid.token.here');
      jwtDecode.mockReturnValue({ exp: Date.now() / 1000 + 3600 });

      const mockAssign = jest.fn();
      Object.defineProperty(window, 'location', { value: { assign: mockAssign }, writable: true });

      const result = await fetchWithAuthHeader('http://example.com/api/data');

      expect(result).toBeNull();
      expect(localStorage.removeItem).toHaveBeenCalledWith('jwt_token');
      expect(mockAssign).toHaveBeenCalledWith('http://example.com/auth/login');
    });
  });
});