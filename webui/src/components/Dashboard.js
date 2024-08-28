import React from 'react';
import { useAuth } from '../contexts/AuthContext';

const Dashboard = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h1>Welcome, {user ? user.name : 'Guest'}!</h1>
      {/* Add more dashboard content here */}
    </div>
  );
};

export default Dashboard;