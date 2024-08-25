import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { handleCallback } from '../services/authService';

const Callback = () => {
  const navigate = useNavigate();

  useEffect(() => {
    handleCallback().then(() => {
      navigate('/');
    });
  }, [navigate]);

  return <div>Loading...</div>;
};

export default Callback;