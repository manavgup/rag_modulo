import React from 'react';
import { Button } from '@carbon/react';
import { signIn } from '../services/authService';

const SignIn = () => {
  return (
    <div className="sign-in-container">
      <h1>Welcome to RAG Modulo</h1>
      <p>Please sign in to continue</p>
      <Button onClick={signIn}>Sign In</Button>
    </div>
  );
};

export default SignIn;