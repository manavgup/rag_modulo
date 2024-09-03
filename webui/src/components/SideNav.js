import React from 'react';
import { SideNav, SideNavItems, SideNavLink } from '@carbon/react';
import { useLocation, useNavigate } from 'react-router-dom';

const UISideNav = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const isActive = (path) => location.pathname === path;

  const onNavigate = (path) => {
    navigate(path);
  };

  return (
    <SideNav isFixedNav expanded={true} isChildOfHeader={false} aria-label="Side navigation">
      <SideNavItems>
        <SideNavLink
          href="#"
          onClick={() => onNavigate('/dashboard')}
          isActive={isActive('/dashboard')}
        >
          Dashboard
        </SideNavLink>
        <SideNavLink
          href="#"
          onClick={() => onNavigate('/create-collection')}
          isActive={isActive('/create-collection')}
        >
          Create New Collection
        </SideNavLink>
        {/* Add more menu items as needed */}
      </SideNavItems>
    </SideNav>
  );
};

export default UISideNav;