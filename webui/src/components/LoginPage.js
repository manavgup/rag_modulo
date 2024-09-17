import React from 'react';
import { Button } from 'carbon-components-react';
import { useAuth } from '../contexts/AuthContext';

const LoginPage = () => {
  const { signIn } = useAuth();

  const handleLogin = () => {
    signIn(); // This will trigger the backend's login process
  };

  return (
    <div className="login-page">
      <Button onClick={handleLogin}>Log in with IBM</Button>
    </div>
  );
};

export default LoginPage;