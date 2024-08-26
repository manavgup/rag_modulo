import React, { useEffect } from 'react';
import { handleCallback } from '../services/authService';

const Callback = () => {
  useEffect(() => {
    const processCallback = async () => {
      try {
        const user = await handleCallback();
        console.log('User info after login:', user);
      } catch (error) {
        console.error('Error during callback processing:', error);
      }
    };
    processCallback();
  }, []);

  return <div>Processing login...</div>;
};

export default Callback;