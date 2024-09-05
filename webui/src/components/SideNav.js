import React from "react";
import { SideNav, SideNavItems, SideNavLink } from "@carbon/react";
import { useLocation, useNavigate } from "react-router-dom";
import { Fade} from '@carbon/icons-react';

const UISideNav = ({ isSideNavExpanded, handleSideNavExpand }) => {
  const location = useLocation();
  const navigate = useNavigate();

  const isActive = (path) => location.pathname === path;

  const onNavigate = (path) => {
    navigate(path);
  };

  return (
    <SideNav
      aria-label="Side navigation"
      isRail
      expanded={isSideNavExpanded}
      onOverlayClick={handleSideNavExpand}
      onSideNavBlur={handleSideNavExpand}
      // onClick={handleSideNavExpanded}
    >
      <SideNavItems>
        <SideNavLink
          renderIcon={Fade}
          href="#"
          onClick={() => onNavigate("/dashboard")}
          isActive={isActive("/dashboard")}
        >
          Dashboard
        </SideNavLink>
        <SideNavLink
          renderIcon={Fade}
          href="#"
          onClick={() => onNavigate("/create-collection")}
          isActive={isActive("/create-collection")}
        >
          Create New Collection
        </SideNavLink>
        {/* Add more menu items as needed */}
      </SideNavItems>
    </SideNav>
  );
};

export default UISideNav;
