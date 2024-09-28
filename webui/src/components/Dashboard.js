import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Tile,
  ClickableTile,
  Loading,
  StructuredListWrapper,
  StructuredListHead,
  StructuredListBody,
  StructuredListRow,
  StructuredListCell,
  Button
} from 'carbon-components-react';
import { Add, Search, Document } from '@carbon/icons-react';
import { getUserCollections } from '../api/api';
import { useNotification } from '../contexts/NotificationContext';
import './Dashboard.css';

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
      const collectionsData = await getUserCollections(1, 5);
      console.log('Fetched collections data:', collectionsData);
      setCollections(collectionsData.data || []);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      addNotification('error', 'Error', 'Failed to load dashboard data. Please try again later.');
      setCollections([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loading description="Loading dashboard" />;
  }

  if (collections.length === 0) {
    return (
      <div className="dashboard">
        <h1>Welcome to IBM RAG Solution</h1>
        <p>No collections found. Start by creating a new collection.</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <h1>Welcome to IBM RAG Solution</h1>
      <div className="dashboard-content">
        <Tile className="dashboard-section">
          <h2>Quick Actions</h2>
          <div className="quick-actions">
            <ClickableTile href="/search">
              <Search />
              <h3>Search Documents</h3>
              <p>Search across all your collections</p>
            </ClickableTile>
            <ClickableTile href="/collections">
              <Add />
              <h3>Create Collection</h3>
              <p>Add a new document collection</p>
            </ClickableTile>
            <ClickableTile href="/upload">
              <Document />
              <h3>Upload Document</h3>
              <p>Add a new document to a collection</p>
            </ClickableTile>
          </div>
        </Tile>
        <Tile className="dashboard-section">
          <h2>Recent Collections</h2>
          <StructuredListWrapper ariaLabel="Recent collections">
            <StructuredListHead>
              <StructuredListRow head>
                <StructuredListCell head>Name</StructuredListCell>
                <StructuredListCell head>Documents</StructuredListCell>
                <StructuredListCell head>Last Updated</StructuredListCell>
              </StructuredListRow>
            </StructuredListHead>
            <StructuredListBody>
              {collections.map((collection) => (
                <StructuredListRow key={collection.id}>
                  <StructuredListCell>
                    <Link to={`/collections/${collection.id}`}>{collection.name}</Link>
                  </StructuredListCell>
                  <StructuredListCell>{collection.documentCount}</StructuredListCell>
                  <StructuredListCell>{new Date(collection.lastUpdated).toLocaleDateString()}</StructuredListCell>
                </StructuredListRow>
              ))}
            </StructuredListBody>
          </StructuredListWrapper>
          <Link to="/collections" className="view-all-link">
            <Button kind="ghost" size="small">View all collections</Button>
          </Link>
        </Tile>
      </div>
    </div>
  );
};

export default Dashboard;
