import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Tile,
  ClickableTile,
  Loading,
  StructuredListWrapper,
  StructuredListHead,
  StructuredListBody,
  StructuredListRow,
  StructuredListCell,
  Button,
} from "carbon-components-react";
import { Add, Search, Document } from "@carbon/icons-react";
import { getUserCollections } from "src/api/api";
import { useNotification } from "src/contexts/NotificationContext";
import "./Dashboard.css";

const Dashboard = () => {
  const [collections, setCollections] = useState([]);
  const [loading, setLoading] = useState(true);
  const { addNotification } = useNotification();

  useEffect(() => {
    fetchDashboardData();
  }, []);


  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const collectionsData = await getUserCollections();
      // console.log("Fetched collections data:", collectionsData.collections);
      setCollections(collectionsData.collections);
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
      addNotification(
        "error",
        "Error",
        "Failed to load dashboard data. Please try again later."
      );
      setCollections([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loading description="Loading dashboard" />;
  }

  if (collections?.length === 0) {
    return (
      <div className="dashboard">
        <h1>Welcome to IBM RAG Solution</h1>
        <p>No collections found. Start by creating a new collection.</p>
      </div>
    );
  }

  return (
    <div className="children-container dashboard">
      <h1>Welcome to IBM RAG Solution</h1>
      <div className="dashboard-content">
        <Tile className="dashboard-section" key="quick-actions">
          <h3>Quick Actions</h3>
          <div className="quick-actions">
            <ClickableTile href="/search">
              <Search />
              <h4>Search Documents</h4>
              <p>Search across all your collections</p>
            </ClickableTile>
            <ClickableTile href="/collections">
              <Add />
              <h4>Create Collection</h4>
              <p>Add a new document collection</p>
            </ClickableTile>
            <ClickableTile href="/upload">
              <Document />
              <h4>Upload Document</h4>
              <p>Add a new document to a collection</p>
            </ClickableTile>
          </div>
        </Tile>
        <Tile className="dashboard-section" key="recent-collections">
          <h3>Recent Collections</h3>
          <StructuredListWrapper aria-label="Recent collections" key="sList">
            <StructuredListHead key="hHead">
              <StructuredListRow key="hHeadRow" head >
                <StructuredListCell key="hName" head>Name</StructuredListCell>
                <StructuredListCell key="hCount" head>Documents</StructuredListCell>
                <StructuredListCell key="hLastUpdated" head>Last Updated</StructuredListCell>
              </StructuredListRow>
            </StructuredListHead>
            <StructuredListBody key="bRow">
              {collections?.map((collection) => (
                <StructuredListRow key={collection.collection_id}>
                  <StructuredListCell key="name">
                    <Link to={`/collections/${collection.id}`}>
                      {collection.name}
                    </Link>
                  </StructuredListCell>
                  <StructuredListCell key="count" > 
                    {collection.documentCount}
                  </StructuredListCell>
                  <StructuredListCell key="lastUpdated">
                    {new Date(collection.lastUpdated).toLocaleDateString()}
                  </StructuredListCell>
                </StructuredListRow>
              ))}
            </StructuredListBody>
          </StructuredListWrapper>
          <Link to="/collections" className="view-all-link">
            <Button kind="ghost">View all collections</Button>
          </Link>
        </Tile>
      </div>
    </div>
  );
};


export default Dashboard;
