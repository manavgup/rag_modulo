import React, { useState } from "react";
import "./SideNav.css";
import {
  SideNav,
  SideNavDivider,
  SideNavItems,
  SideNavLink,
  SideNavMenu,
  SideNavMenuItem
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
  SettingsAdjust
} from "@carbon/icons-react";

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
        >
          <div className="side-nav-menu-item">
            <Dashboard size={16} />
            <span>Dashboard</span>
          </div>
        </SideNavLink>
        <SideNavLink
          href="#"
          onClick={() => onNavigate("/collections")}
          isActive={isActive("/collections")}
        >
          <div className="side-nav-menu-item">
            <ModelAlt size={16} />
            <span>Collections</span>
          </div>
        </SideNavLink>
        <SideNavLink
          href="#"
          onClick={() => onNavigate("/search")}
          isActive={isActive("/search")}
        >
          <div className="side-nav-menu-item">
            <Search size={16} />
            <span>Search Documents</span>
          </div>
        </SideNavLink>
        
        <SideNavDivider />
        
        <SideNavMenu
          isActive={isConfigActive()}
          defaultExpanded={true}
          onToggle={() => setIsConfigExpanded(!isConfigExpanded)}
          title={
            <div className="side-nav-menu-item">
              <Settings size={16} />
              <span>Configuration</span>
            </div>
          }
        >
          <SideNavMenuItem
            onClick={() => onNavigate("/configuration/providers")}
            isActive={isActive("/configuration/providers")}
          >
            <div className="side-nav-menu-item">
              <Cloud size={16} />
              <span>Provider Settings</span>
            </div>
          </SideNavMenuItem>
          <SideNavMenuItem
            onClick={() => onNavigate("/configuration/pipeline")}
            isActive={isActive("/configuration/pipeline")}
          >
            <div className="side-nav-menu-item">
              <Flow size={16} />
              <span>Pipeline Settings</span>
            </div>
          </SideNavMenuItem>
          <SideNavMenuItem
            onClick={() => onNavigate("/configuration/llm")}
            isActive={isActive("/configuration/llm")}
          >
            <div className="side-nav-menu-item">
              <SettingsAdjust size={16} />
              <span>LLM Parameters</span>
            </div>
          </SideNavMenuItem>
          <SideNavMenuItem
            onClick={() => onNavigate("/configuration/templates")}
            isActive={isActive("/configuration/templates")}
          >
            <div className="side-nav-menu-item">
              <Template size={16} />
              <span>Prompt Templates</span>
            </div>
          </SideNavMenuItem>
        </SideNavMenu>
      </SideNavItems>
    </SideNav>
  );
};

export default UISideNav;
