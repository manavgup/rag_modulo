import React, { useEffect, useState, useCallback, memo } from 'react';
import { signIn, signOut, getUser, loadIBMScripts } from '../services/authService';

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

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const userData = await getUser();
        if (userData && userData.user) {
          setUser(userData.user);
        }
      } catch (err) {
        console.error('Error fetching user:', err);
        setError('Failed to fetch user information');
      }
    };

    fetchUser();
  }, []);

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