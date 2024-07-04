// components/SideNav.js
import React from 'react';
import {
  SideNav,
  SideNavItems,
  SideNavLink,
  SideNavMenu,
  SideNavMenuItem,
} from '@carbon/react';

const UISideNav = ({ expanded, onNavigate }) => (
  <SideNav aria-label="Side navigation" expanded={expanded} isPersistent={false}>
    <SideNavItems>
      <SideNavLink href="#" onClick={(e) => onNavigate(e, 'dashboard')}>Chat with Documents</SideNavLink>
      <SideNavMenu title="Collections" isActive={false}>
        <SideNavMenuItem href="#" onClick={(e) => onNavigate(e, 'report1')}>Create New...</SideNavMenuItem>
        <SideNavMenuItem href="#" onClick={(e) => onNavigate(e, 'report2')}>Report 2</SideNavMenuItem>
      </SideNavMenu>
      <SideNavLink href="#" onClick={(e) => onNavigate(e, 'settings')}>Settings</SideNavLink>
    </SideNavItems>
  </SideNav>
);

export default UISideNav;