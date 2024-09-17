import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Header as CarbonHeader,
  HeaderName,
  HeaderNavigation,
  HeaderMenuItem,
  HeaderGlobalBar,
  HeaderGlobalAction,
  SkipToContent,
} from 'carbon-components-react';
import { User, Logout } from '@carbon/icons-react';
import { useAuth } from '../contexts/AuthContext';
import './Header.css';

const Header = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const location = useLocation();

  const isActive = (path) => {
    return location.pathname === path ? 'active' : '';
  };

  return (
    <CarbonHeader aria-label="IBM RAG Solution">
      <SkipToContent />
      <HeaderName element={Link} to="/" prefix="IBM">
        RAG Solution
      </HeaderName>
      <HeaderNavigation aria-label="IBM RAG Solution">
        <HeaderMenuItem element={Link} to="/" className={isActive('/')}>
          Dashboard
        </HeaderMenuItem>
        <HeaderMenuItem element={Link} to="/search" className={isActive('/search')}>
          Search
        </HeaderMenuItem>
        <HeaderMenuItem element={Link} to="/collections" className={isActive('/collections')}>
          Collections
        </HeaderMenuItem>
      </HeaderNavigation>
      <HeaderGlobalBar>
        {isAuthenticated && (
          <>
            <HeaderGlobalAction aria-label="User" tooltipAlignment="end" onClick={() => {}}>
              <User />
            </HeaderGlobalAction>
            <HeaderGlobalAction aria-label="Logout" tooltipAlignment="end" onClick={logout}>
              <Logout />
            </HeaderGlobalAction>
          </>
        )}
      </HeaderGlobalBar>
    </CarbonHeader>
  );
};

export default Header;
