import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { Theme, Content } from '@carbon/react';
import UIHeader from './components/Header.js';
import UISideNav from './components/SideNav';
import HomePage from './pages/HomePage';
import './App.css';

function App() {
  return (
    <Theme theme="g100">
      <Router>
        <div className="App">
          <UIHeader />
          <div className="content-wrapper">
            <UISideNav />
            <Content className="main-content">
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/about" element={<div>About Page</div>} />
                <Route path="/dashboard" element={<div>Dashboard Page</div>} />
                <Route path="/settings" element={<div>Settings Page</div>} />
              </Routes>
            </Content>
          </div>
        </div>
      </Router>
    </Theme>
  );
}

export default App;