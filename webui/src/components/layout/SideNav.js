import React, { useState } from "react";
import {
  SideNav,
  SideNavItems,
  SideNavLink,
  SideNavMenu
} from "@carbon/react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Search,
  ModelAlt,
  Dashboard,
  Settings,
  Flow,
  Template,
  Cloud,
  SettingsAdjust,
} from "@carbon/icons-react";

import "./SideNav.css";

const UISideNav = ({ isSideNavExpanded, handleSideNavExpand }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isConfigExpanded, setIsConfigExpanded] = useState(true);

  const isActive = (path) => location.pathname === path;
  const isConfigActive = () => location.pathname.startsWith("/configuration");

  const onNavigate = (path) => {
    navigate(path);
  };

  return (
    <SideNav
      aria-label="Side navigation"
      expanded={isSideNavExpanded}
      onOverlayClick={handleSideNavExpand}
      onSideNavBlur={handleSideNavExpand}
      isRail={false}
      isPersistent={true}
    >
      <SideNavItems>
        <SideNavLink
          href="#"
          onClick={() => onNavigate("/dashboard")}
          isActive={isActive("/dashboard")}
          renderIcon={Dashboard}
        >
          Dashboard
        </SideNavLink>
        <SideNavLink
          href="#"
          onClick={() => onNavigate("/collections")}
          isActive={isActive("/collections")}
          renderIcon={ModelAlt}
        >
          Collections
        </SideNavLink>
        <SideNavLink
          href="#"
          onClick={() => onNavigate("/search")}
          isActive={isActive("/search")}
          renderIcon={Search}
        >
          Search Documents
        </SideNavLink>

        <SideNavMenu
          isActive={isConfigActive()}
          defaultExpanded={true}
          expanded={isConfigExpanded}
          onToggle={() => setIsConfigExpanded(!isConfigExpanded)}
          renderIcon={Settings}
          title="Configuration"
          className="side-nav-menu"
        >
          <SideNavLink
            href="#"
            onClick={() => onNavigate("/configuration/providers")}
            isActive={isActive("/configuration/providers")}
            renderIcon={Cloud}
          >
            Provider Settings
          </SideNavLink>
          <SideNavLink
            href="#"
            onClick={() => onNavigate("/configuration/pipeline")}
            isActive={isActive("/configuration/pipeline")}
            renderIcon={Flow}
          >
            Pipeline Settings
          </SideNavLink>
          <SideNavLink
            href="#"
            onClick={() => onNavigate("/configuration/llm")}
            isActive={isActive("/configuration/llm")}
            renderIcon={SettingsAdjust}
          >
            LLM Parameters
          </SideNavLink>
          <SideNavLink
            href="#"
            onClick={() => onNavigate("/configuration/templates")}
            isActive={isActive("/configuration/templates")}
            renderIcon={Template}
          >
            Prompt Templates
          </SideNavLink>
        </SideNavMenu>
      </SideNavItems>
    </SideNav>
  );
};

export default UISideNav;
