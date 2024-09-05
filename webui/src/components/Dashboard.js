import React from "react";
import { useAuth } from "../contexts/AuthContext";
import { Content, Theme } from "@carbon/react";

const Dashboard = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <Content>
      <h1>Welcome, {user ? user.name : "Guest"}!</h1>
      {/* Add more dashboard content here */}
    </Content>
  );
};

export default Dashboard;
