import React, { useState } from 'react';
import { Button, Loading } from 'carbon-components-react';
import  { getFullApiUrl, API_ROUTES } from '../config/config';
import './LoginPage.css';

// console.log('LoginPage component loaded with config:', config);

const LoginPage = () => {
  // const { signIn, user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  // useEffect(() => {
  //   console.log('LoginPage mounted, user:', user);
  //   console.log('Current API URL:', config.apiUrl);
  //   console.log('Full login URL:', getFullApiUrl(API_ROUTES.LOGIN));
  // }, [user]);

  const handleLogin = () => {
    setIsLoading(true);
    try {
      const loginUrl = getFullApiUrl(API_ROUTES.LOGIN);
      // console.log('Redirecting to:', loginUrl);
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