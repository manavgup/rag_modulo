import React, { useState } from "react";
import {
  Header as CarbonHeader,
  HeaderName,
  HeaderGlobalBar,
  HeaderGlobalAction,
  HeaderPanel,
  Theme,
  UnorderedList,
  ListItem,
} from "@carbon/react";
import { Menu, UserAvatar, CloseLarge, List } from "@carbon/icons-react";
import { useAuth } from "src/contexts/AuthContext";

import UISideNav from "./SideNav";
import "./Header.css";

const Header = () => {
  const { user, signOut } = useAuth();

  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isMainMenuOpen, setIsMainMenuOpen] = useState(false);

  const handleMainMenuOpen = () => {
    // console.log(isMainMenuOpen);
    setIsMainMenuOpen((prevState) => !prevState);
  };

  const handleUserMenuClick = () => {
    setIsUserMenuOpen((prevState) => !prevState);
  };

  const handleLogout = () => {
    signOut();
    setIsUserMenuOpen(false);
  };

  return (
    <Theme theme="g100">
      <CarbonHeader aria-label="RAG Modulo">
        <HeaderGlobalAction aria-label="" onClick={handleMainMenuOpen}>
          {isMainMenuOpen ? <CloseLarge size={20} /> : <Menu size={20} />}
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
            <UserAvatar size={24} />
          </HeaderGlobalAction>
        </HeaderGlobalBar>
        {isUserMenuOpen && (
          <HeaderPanel
            expanded
            aria-label="User Menu"
            className="user-menu-panel"
          >
            <div className="user-menu">
              <UnorderedList className="user-menu-list">
                {user ? (
                  <>
                    <ListItem key="username" className="user-menu-username"> {user.name || "User"} </ListItem>
                    <ListItem key="profile"> Profile </ListItem>
                    <ListItem key="settings"> Settings </ListItem>
                    <ListItem key="logout" className="user-menu-logout">
                      <a href="#" onClick={handleLogout}>Logout</a>
                    </ListItem>
                  </>
                ) : (
                  <ListItem key="signin" className="user-menu-signin">
                    <a href="/signin">Sign In</a>
                  </ListItem>
                )}
              </UnorderedList>
            </div>
          </HeaderPanel>
        )}
        <UISideNav
          isSideNavExpanded={isMainMenuOpen}
          handleSideNavExpand={handleMainMenuOpen}
        />
      </CarbonHeader>
    </Theme>
  );
};

export default Header;
