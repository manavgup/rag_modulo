import React, { useState } from 'react';
import {
  Header as CarbonHeader,
  HeaderName,
  HeaderGlobalBar,
  HeaderGlobalAction,
  HeaderPanel,
  Theme
} from '@carbon/react';
import { Menu, UserAvatar } from '@carbon/icons-react';
import { useAuth } from '../contexts/AuthContext';

const Header = ({ onMenuClick }) => {
  const { user, logout } = useAuth();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  const handleUserMenuClick = () => {
    setIsUserMenuOpen(prevState => !prevState);
  };

  const handleLogout = () => {
    logout();
    setIsUserMenuOpen(false);
  };

  return (
    <Theme theme="g100">
      <CarbonHeader aria-label="RAG Modulo">
        <HeaderGlobalAction aria-label="Menu" onClick={onMenuClick}>
          <Menu size={20} />
        </HeaderGlobalAction>
        <HeaderName href="#" prefix="">
          RAG Modulo
        </HeaderName>
        <HeaderGlobalBar>
          <HeaderGlobalAction
            aria-label="User Avatar"
            onClick={handleUserMenuClick}
            isActive={isUserMenuOpen}
          >
            <UserAvatar />
          </HeaderGlobalAction>
        </HeaderGlobalBar>
        {isUserMenuOpen && (
          <HeaderPanel expanded aria-label="User Menu" className="user-menu-panel">
            <div className="user-menu">
              {user ? (
                <>
                  <p>{user.name || 'User'}</p>
                  <button onClick={handleLogout}>Logout</button>
                </>
              ) : (
                <a href="/signin">Sign In</a>
              )}
            </div>
          </HeaderPanel>
        )}
      </CarbonHeader>
    </Theme>
  );
};

export default Header;