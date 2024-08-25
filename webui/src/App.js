import React, { useEffect, useState, Suspense } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import { Theme, Content } from '@carbon/react';
import UIHeader from './components/Header';
import UISideNav from './components/SideNav';
import SignIn from './components/SignIn';
import Dashboard from './components/Dashboard';
import CollectionForm from './components/CollectionForm';
import Callback from './components/Callback';
import { getUser } from './services/authService';
import './App.css';
import './css/common.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUser().then(user => {
      setUser(user);
      setLoading(false);
    }).catch(error => {
      console.error('Error fetching user:', error);
      setLoading(false);
    });
  }, []);

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
                  <Route path="/callback" element={<Callback />} />
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

export default App;