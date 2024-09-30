import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { Content } from 'carbon-components-react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { NotificationProvider } from './contexts/NotificationContext';
import Header from './components/Header';
import Footer from './components/Footer';
import Dashboard from './components/Dashboard';
import SearchInterface from './components/SearchInterface';
import CollectionBrowser from './components/CollectionBrowser';
import DocumentViewer from './components/DocumentViewer';
import LoginPage from './components/LoginPage';
import { handleAuthCallback } from './services/authService';
import config from './config/config';
import './App.css';
import './styles/global.css';

console.log('App.js loaded', { config });

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  const location = useLocation();
  
  console.log('ProtectedRoute - user:', user, 'loading:', loading, 'location:', location);

  if (loading) {
    return <div>Loading...</div>;
  }
  
  if (!user) {
    console.log('ProtectedRoute - Redirecting to login');
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

const AppLayout = ({ children }) => {
  const { user } = useAuth();

  console.log('AppLayout - user:', user);

  return (
    <div className="app-container">
      {user && <Header />}
      <Content>
        <div className="page-container">
          {children}
        </div>
      </Content>
      {user && <Footer />}
    </div>
  );
};

function AuthCallback() {
  const navigate = useNavigate();
  const { fetchUser } = useAuth();

  console.log('AuthCallback component rendered');

  useEffect(() => {
    const processCallback = async () => {
      console.log('Processing auth callback');
      const result = handleAuthCallback();
      if (result.success) {
        console.log('Auth callback successful, fetching user');
        await fetchUser();
        navigate('/');
      } else {
        console.log('Auth callback failed, redirecting to login');
        navigate('/login');
      }
    };

    processCallback();
  }, [fetchUser, navigate]);

  return <div>Processing authentication...</div>;
}

function AppContent() {
  const { user, loading, fetchUser } = useAuth();
  const location = useLocation();

  console.log('AppContent - user:', user, 'loading:', loading, 'location:', location);

  useEffect(() => {
    if (!user && !loading) {
      console.log('AppContent - Fetching user');
      fetchUser();
    }
  }, [user, loading, fetchUser]);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/callback" element={<AuthCallback />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/search"
        element={
          <ProtectedRoute>
            <SearchInterface />
          </ProtectedRoute>
        }
      />
      <Route
        path="/collections"
        element={
          <ProtectedRoute>
            <CollectionBrowser />
          </ProtectedRoute>
        }
      />
      <Route
        path="/document/:id"
        element={
          <ProtectedRoute>
            <DocumentViewer />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  console.log('App component rendered', { windowLocation: window.location });

  return (
    <AuthProvider>
      <NotificationProvider>
        <Router>
          <AppLayout>
            <AppContent />
          </AppLayout>
        </Router>
      </NotificationProvider>
    </AuthProvider>
  );
}

export default App;
