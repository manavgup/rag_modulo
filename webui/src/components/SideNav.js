import React from 'react';
import { SideNav, SideNavItems, SideNavLink } from '@carbon/react';

const UISideNav = ({ expanded, onNavigate, currentPage }) => {
  return (
    <SideNav isFixedNav expanded={expanded} isChildOfHeader={false} aria-label="Side navigation">
      <SideNavItems>
        <SideNavLink
          href="#"
          onClick={(e) => onNavigate(e, 'dashboard')}
          isActive={currentPage === 'dashboard'}
        >
          Dashboard
        </SideNavLink>
        <SideNavLink
          href="#"
          onClick={(e) => onNavigate(e, 'create')}
          isActive={currentPage === 'create'}
        >
          Create New Collection
        </SideNavLink>
        <SideNavLink
          href="#"
          onClick={(e) => onNavigate(e, 'report1')}
          isActive={currentPage === 'report1'}
        >
          Report 1
        </SideNavLink>
        <SideNavLink
          href="#"
          onClick={(e) => onNavigate(e, 'report2')}
          isActive={currentPage === 'report2'}
        >
          Report 2
        </SideNavLink>
      </SideNavItems>
    </SideNav>
  );
};

export default UISideNav;