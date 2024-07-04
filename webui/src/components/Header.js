import React from 'react';
import {
  Header as CarbonHeader,
  HeaderName,
  HeaderGlobalBar,
  HeaderGlobalAction,
} from '@carbon/react'
import { Menu, UserAvatar } from '@carbon/icons-react';

const Header = ({ onMenuClick, onSettingsClick }) => (
  <CarbonHeader aria-label="RAG Modulo">
    <HeaderGlobalAction aria-label="Menu" onClick={onMenuClick}>
      <Menu size={20} />
    </HeaderGlobalAction>
    <HeaderName href="#" prefix="">
      RAG Modulo
    </HeaderName>
    <HeaderGlobalBar>
      <HeaderGlobalAction aria-label="Settings" onClick={onSettingsClick}>
        Settings
      </HeaderGlobalAction>
      <HeaderGlobalAction aria-label="User Avatar">
        <UserAvatar />
      </HeaderGlobalAction>
    </HeaderGlobalBar>
  </CarbonHeader>
);

export default Header;