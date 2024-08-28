import React, { Suspense } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import { Theme, Content } from '@carbon/react';
import UIHeader from './components/Header';
import UISideNav from './components/SideNav';
import SignIn from './components/SignIn';
import Dashboard from './components/Dashboard';
import CollectionForm from './components/CollectionForm';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import './App.css';
import './css/common.css';

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <Theme theme="g100">
      <Router>
        <Suspense fallback={<div>Loading...</div>}>
          <div className="App">
            {user && <UIHeader />}
            <div className="content-wrapper">
              {user && <UISideNav />}
              <Content className="main-content">
                <Routes>
                  <Route path="/signin" element={user ? <Navigate to="/dashboard" /> : <SignIn />} />
                  <Route
                    path="/dashboard"
                    element={user ? <Dashboard /> : <Navigate to="/signin" />}
                  />
                  <Route
                    path="/create-collection"
                    element={user ? <CollectionForm /> : <Navigate to="/signin" />}
                  />
                  <Route path="/" element={<Navigate to={user ? "/dashboard" : "/signin"} />} />
                </Routes>
              </Content>
            </div>
          </div>
        </Suspense>
      </Router>
    </Theme>
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