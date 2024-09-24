import React, { useEffect } from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
  useNavigate,
  useLocation,
  useParams,
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
import "./App.css";
import "./styles/global.css";

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  return user ? children : <Navigate to="/login" />;
};

const AppLayout = ({ children }) => {
  return (
    <div className="app-container">
      <Header />
      <Content>
        <div className="page-container">{children}</div>
      </Content>
      <Footer />
    </div>
  );
};

function AuthCallback() {
  // const navigate = useNavigate();
  // const { fetchUser } = useAuth();
  // useEffect(() => {
  //   const processCallback = async () => {
  //     const success = handleAuthCallback();
  //     if (success) {
  //       await fetchUser();
  //       navigate("/");
  //     } else {
  //       navigate("/login");
  //     }
  //   };
  //   processCallback();
  // }, [fetchUser, navigate]);
  // return <div>Processing authentication...</div>;
}

function AppContent() {
  const { user, loading } = useAuth();
  const location = useLocation();

  const navigate = useNavigate();
  const { fetchUser } = useAuth();
  const url_params = new URLSearchParams(window.location.search);

  /**
   * Handles the callback from the authentication server after the user has
   * authorized the application.
   *
   * If the callback is successful, it will set the user's id_token in local
   * storage and navigate to the main page.
   *
   * If the callback fails, it will navigate to the login page.
   */
  const ProcessCallback = async () => {
    if (url_params.entries > 0 || url_params.get("id_token")) {
      console.log("Processing callback...");
      localStorage.setItem("access_token", url_params.get("access_token"));
      localStorage.setItem("id_token", url_params.get("id_token"));
      localStorage.setItem("expires_in", url_params.get("expires_in"));
      localStorage.setItem("user_id", url_params.get("user_id"));

      navigate("/");

      // const success = handleAuthCallback();
      // if (success) {
      //   await fetchUser();
      //   navigate("/");
      // } else {
      //   navigate("/login");
      // }
    }
  };

  useEffect(() => {
    ProcessCallback();
  }, [fetchUser, navigate]);

  if (loading && location.pathname !== "/callback") {
    return <div>Loading...</div>;
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/" /> : <LoginPage />}
      />
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
      {/* Add more routes as needed */}
    </Routes>
  );
}

function App() {
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
