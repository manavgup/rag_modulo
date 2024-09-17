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
import { getUserCollections, getRecentDocuments, getUsageStatistics } from '../api/api';
import { useNotification } from '../contexts/NotificationContext';
import './Dashboard.css';

const Dashboard = () => {
  const [collections, setCollections] = useState([]);
  const [recentDocuments, setRecentDocuments] = useState([]);
  const [usageStats, setUsageStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const { addNotification } = useNotification();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [collectionsData, documentsData, statsData] = await Promise.all([
        getUserCollections(1, 5),
        getRecentDocuments(5),
        getUsageStatistics()
      ]);
      setCollections(collectionsData.data);
      setRecentDocuments(documentsData);
      setUsageStats(statsData);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      addNotification('error', 'Error', 'Failed to load dashboard data. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loading description="Loading dashboard" />;
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
          {collections.length > 0 ? (
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
          ) : (
            <p>No collections found. Start by creating a new collection.</p>
          )}
          <Link to="/collections" className="view-all-link">
            <Button kind="ghost" size="small">View all collections</Button>
          </Link>
        </Tile>
        <Tile className="dashboard-section">
          <h2>Recent Documents</h2>
          {recentDocuments.length > 0 ? (
            <StructuredListWrapper ariaLabel="Recent documents">
              <StructuredListHead>
                <StructuredListRow head>
                  <StructuredListCell head>Name</StructuredListCell>
                  <StructuredListCell head>Collection</StructuredListCell>
                  <StructuredListCell head>Last Modified</StructuredListCell>
                </StructuredListRow>
              </StructuredListHead>
              <StructuredListBody>
                {recentDocuments.map((document) => (
                  <StructuredListRow key={document.id}>
                    <StructuredListCell>
                      <Link to={`/document/${document.id}`}>{document.name}</Link>
                    </StructuredListCell>
                    <StructuredListCell>{document.collectionName}</StructuredListCell>
                    <StructuredListCell>{new Date(document.lastModified).toLocaleDateString()}</StructuredListCell>
                  </StructuredListRow>
                ))}
              </StructuredListBody>
            </StructuredListWrapper>
          ) : (
            <p>No recent documents found.</p>
          )}
        </Tile>
        {usageStats && (
          <Tile className="dashboard-section">
            <h2>Usage Statistics</h2>
            <div className="usage-stats">
              <div className="stat-item">
                <h3>{usageStats.totalDocuments}</h3>
                <p>Total Documents</p>
              </div>
              <div className="stat-item">
                <h3>{usageStats.totalCollections}</h3>
                <p>Total Collections</p>
              </div>
              <div className="stat-item">
                <h3>{usageStats.searchesLastWeek}</h3>
                <p>Searches (Last 7 days)</p>
              </div>
              <div className="stat-item">
                <h3>{usageStats.storageUsed}</h3>
                <p>Storage Used</p>
              </div>
            </div>
          </Tile>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
