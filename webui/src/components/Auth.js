// src/components/Auth.js

import React, { useEffect, useState } from 'react';
import { signIn, signOut, getUser } from '../services/authService';

const Auth = () => {
  const [user, setUser] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getUser()
      .then(setUser)
      .catch(err => {
        console.error('Error fetching user:', err);
        setError('Failed to fetch user information');
      });
  }, []);

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!user) {
    return <button onClick={signIn}>Sign In</button>;
  }

  return (
    <div>
      <p>Welcome, {user.profile.name}!</p>
      <button onClick={signOut}>Sign Out</button>
    </div>
  );
};

export default Auth;