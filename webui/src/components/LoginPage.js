import React, { useState } from 'react';
import { Button, Loading } from '@carbon/react';
import  { getFullApiUrl, API_ROUTES } from '../config/config';
import './LoginPage.css';

const LoginPage = () => {
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = () => {
    setIsLoading(true);
    try {
      const loginUrl = getFullApiUrl(API_ROUTES.LOGIN);
      window.location.href = loginUrl;
    } catch (error) {
      console.error('Login failed:', error);
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <h1>Welcome to RAG Modulo</h1>
        <p>Please sign in with your IBM account to access the application.</p>
        {isLoading ? (
          <Loading description="Redirecting to login..." withOverlay={false} />
        ) : (
          <Button onClick={handleLogin}>Log in with IBM</Button>
        )}
      </div>
    </div>
  );
};

export default LoginPage;