import React, { Suspense } from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
} from "react-router-dom";
import { Content, GlobalTheme, Theme } from "@carbon/react";
import UIHeader from "./components/Header";
import SignIn from "./components/SignIn";
import Dashboard from "./components/Dashboard";
import CollectionForm from "./components/CollectionForm";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Collections from "./components/Collections";


import "./styles/common.css";
import "./styles/global.scss";

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <GlobalTheme theme="white">
      <Router>
        <Suspense fallback={<div>Loading...</div>}>
          <div className="App">
            {user && <UIHeader />}
            {/* <div className="content-wrapper "> */}
              <Content
                // className={"main-content"}
              >
                <Routes>
                  <Route
                    path="/signin"
                    element={user ? <Navigate to="/dashboard" /> : <SignIn />}
                  />
                  <Route
                    path="/dashboard"
                    element={user ? <Dashboard /> : <Navigate to="/signin" />}
                  />
                  <Route
                    path="/create-collection"
                    element={
                      user ? <CollectionForm /> : <Navigate to="/signin" />
                    }
                  />
                  <Route
                    path="/collections"
                    element={
                      user ? <Collections /> : <Navigate to="/signin" />
                    }
                  />
                  <Route
                    path="/"
                    element={<Navigate to={user ? "/dashboard" : "/signin"} />}
                  />
                </Routes>
              </Content>
            </div>
          {/* </div> */}
        </Suspense>
      </Router>
    </GlobalTheme>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
