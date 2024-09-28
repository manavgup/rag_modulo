import React, { useEffect, useState, useCallback, memo } from 'react';
import { signIn, signOut, getUserData, loadIBMScripts, handleAuthCallback } from '../services/authService';

const ErrorMessage = memo(({ message }) => <div>Error: {message}</div>);
const SignInButton = memo(({ onSignIn }) => <button onClick={onSignIn}>Sign In</button>);
const UserInfo = memo(({ name, onSignOut }) => (
  <div>
    <p>Welcome, {name}!</p>
    <button onClick={onSignOut}>Sign Out</button>
  </div>
));

const Auth = () => {
  loadIBMScripts();
  const [user, setUser] = useState(null);
  const [error, setError] = useState(null);

  const fetchUser = useCallback(async () => {
    try {
      const userData = await getUserData();
      if (userData) {
        setUser(userData);
      } else {
        setUser(null);
      }
    } catch (err) {
      console.error('Error fetching user:', err);
      setError('Failed to fetch user information');
    }
  }, []);

  useEffect(() => {
    const authSuccess = handleAuthCallback();
    if (authSuccess) {
      fetchUser();
    } else {
      fetchUser(); // Still try to fetch user data in case they're already authenticated
    }
  }, [fetchUser]);

  const handleSignIn = useCallback(() => {
    signIn().catch(err => {
      console.error('Error signing in:', err);
      setError('Failed to sign in');
    });
  }, []);

  const handleSignOut = useCallback(() => {
    signOut().then(() => setUser(null)).catch(err => {
      console.error('Error signing out:', err);
      setError('Failed to sign out');
    });
  }, []);

  if (error) {
    return <ErrorMessage message={error} />;
  }

  if (!user) {
    return <SignInButton onSignIn={handleSignIn} />;
  }

  return <UserInfo name={user.name} onSignOut={handleSignOut} />;
};

export default memo(Auth);