import React, { useEffect } from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";
import { Content } from "carbon-components-react";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { NotificationProvider } from "./contexts/NotificationContext";
import Header from "./components/Header";
import Footer from "./components/Footer";
import Dashboard from "./components/Dashboard";
import SearchInterface from "./components/SearchInterface";
import CollectionBrowser from "./components/CollectionBrowser";
import DocumentViewer from "./components/DocumentViewer";
import LoginPage from "./components/LoginPage";
import { handleAuthCallback } from "./services/authService";
import Collections from "./components/collection/Collections";

import "./App.css";
import "./styles/global.css";
import CollectionForm from "./components/CollectionForm";

function AuthCallback() {
  const navigate = useNavigate();
  const { fetchUser } = useAuth();

  useEffect(() => {
    const processCallback = async () => {
      const result = await handleAuthCallback();
      if (result.success) {
        await fetchUser();
        navigate("/");
      } else {
        navigate("/login");
      }
    };

    processCallback();
  }, [fetchUser, navigate]);

  return <div>Processing authentication...</div>;
}

const AppLayout = ({ children }) => {
  const { user, fetchUser } = useAuth();

  useEffect(() => {
    if (!user) {
      fetchUser();
    }
  }, []);

  return (
    <div className="app-container">
      {user && <Header />}
      <Content className="page-container">{children}</Content>
      {user && <Footer />}
    </div>
  );
};

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

function AppContent() {
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
        path="/document-collections"
        element={
          <ProtectedRoute>
            <CollectionBrowser />
          </ProtectedRoute>
        }
      />
      <Route
        path="/collections"
        element={
          <ProtectedRoute>
            <Collections />
          </ProtectedRoute>
        }
      >
        <Route path="view" element={<CollectionBrowser />}></Route>
        <Route path="create" element={<CollectionForm />}></Route>
        <Route path="edit" element={<CollectionForm />}></Route>
      </Route>
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

const App = () => {
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
};

export default App;
