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
import Header from "./components/layout/Header";
import Footer from "./components/layout/Footer";
import Dashboard from "./components/dashboard/Dashboard";
import SearchInterface from "./components/common/SearchInterface";
import DocumentViewer from "./components/document/DocumentViewer";
import LoginPage from "./components/LoginPage";
import ConfigurationPage from "./components/configuration/ConfigurationPage";
import LLMParameters from "./components/configuration/LLMParameters";
import PromptTemplates from "./components/configuration/PromptTemplates";
import PipelineSettings from "./components/configuration/PipelineSettings";
import ProviderSettings from "./components/configuration/ProviderSettings";
import { handleAuthCallback } from "./services/authService";

import Collection from "./components/collection/Collection";

import "./App.css";
import "./styles/global.css";

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
    <div className="app-container" id="app-container">
      {user && <Header />}
      <div className="page-container">
        <Content>{children}</Content>
      </div>
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

const AppContent = () => {
  return (
    <Routes>
      {/* Auth Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/callback" element={<AuthCallback />} />

      {/* Main Routes */}
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
            <Collection />
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

      {/* Configuration Routes */}
      <Route
        path="/configuration/*"
        element={
          <ProtectedRoute>
            <ConfigurationPage />
          </ProtectedRoute>
        }
      >
        <Route path="providers" element={<ProviderSettings />} />
        <Route path="pipeline" element={<PipelineSettings />} />
        <Route path="llm" element={<LLMParameters />} />
        <Route path="templates" element={<PromptTemplates />} />
        <Route index element={<Navigate to="providers" replace />} />
      </Route>

      {/* Fallback Route */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

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
