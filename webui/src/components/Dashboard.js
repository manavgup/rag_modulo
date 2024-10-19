import React, { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { Content, Theme, Loading, Tile, InlineNotification } from "@carbon/react";
import { getUserCollections } from "../api/api";

const Dashboard = () => {
  const { user, loading } = useAuth();
  const [collections, setCollections] = useState([]);
  const [fetchingCollections, setFetchingCollections] = useState(false);
  const [error, setError] = useState(null);
  const [rawData, setRawData] = useState(null);

  useEffect(() => {
    if (user) {
      fetchUserCollections();
    }
  }, [user]);

  const fetchUserCollections = async () => {
    setFetchingCollections(true);
    setError(null);
    setRawData(null);
    try {
      console.log("Fetching collections for user:", user);
      const data = await getUserCollections();
      console.log("Received data:", data);
      setRawData(data);
      if (Array.isArray(data.collections)) {
        setCollections(data.collections);
      } else {
        console.error("Unexpected data format:", data);
        setError("Received unexpected data format from the server.");
      }
    } catch (error) {
      console.error("Error fetching user collections:", error);
      setError(error.message || "An error occurred while fetching collections.");
    } finally {
      setFetchingCollections(false);
    }
  };

  if (loading || fetchingCollections) {
    return <Loading />;
  }

  return (
    <Content>
      <h1>Welcome, {user ? user.name : "Guest"}!</h1>
      <h2>Your Collections</h2>
      {error && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
        />
      )}
      {collections.length === 0 ? (
        <p>You don't have any collections yet.</p>
      ) : (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
          {collections.map((collection) => (
            <Tile key={collection.id}>
              <h3>{collection.name}</h3>
              <p>Files: {collection.files.length}</p>
            </Tile>
          ))}
        </div>
      )}
      {rawData && (
        <div>
          <h3>Raw Response Data:</h3>
          <pre>{JSON.stringify(rawData, null, 2)}</pre>
        </div>
      )}
    </Content>
  );
};

export default Dashboard;
