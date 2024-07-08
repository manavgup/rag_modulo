// components/SideNav.js
import React from 'react';
import { SideNav, SideNavItems, SideNavLink } from '@carbon/react';

const UISideNav = ({ expanded, onNavigate }) => {
  return (
    <SideNav isFixedNav expanded={expanded} isChildOfHeader={false}>
      <SideNavItems>
        <SideNavLink href="#" onClick={(e) => onNavigate(e, 'dashboard')}>
          Dashboard
        </SideNavLink>
        <SideNavLink href="#" onClick={(e) => onNavigate(e, 'create')}>
          Create New Collection
        </SideNavLink>
        <SideNavLink href="#" onClick={(e) => onNavigate(e, 'settings')}>
          Settings
        </SideNavLink>
      </SideNavItems>
    </SideNav>
  );
};

export default UISideNav;
